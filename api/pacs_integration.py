"""
PACS/DICOM Integration Module

Handles communication with hospital PACS systems:
- Query/Retrieve studies from PACS (C-FIND, C-MOVE)
- Send AI predictions back to PACS (C-STORE)
- DICOM file parsing and metadata extraction
- Automatic study monitoring and processing

Dependencies: pydicom, pynetdicom
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import json

try:
    import pydicom
    from pynetdicom import AE, evt, StoragePresentationContexts
    from pynetdicom.sop_class import (
        PatientRootQueryRetrieveInformationModelFind,
        PatientRootQueryRetrieveInformationModelMove,
        StudyRootQueryRetrieveInformationModelFind,
        StudyRootQueryRetrieveInformationModelMove,
    )
    DICOM_AVAILABLE = True
except ImportError:
    DICOM_AVAILABLE = False
    print("Warning: pydicom/pynetdicom not installed. PACS integration disabled.")
    print("Install with: pip install pydicom pynetdicom")

logger = logging.getLogger(__name__)


class PACSConfig:
    """PACS connection configuration"""
    
    def __init__(self):
        self.enabled = os.getenv('PACS_ENABLED', 'false').lower() == 'true'
        self.host = os.getenv('PACS_HOST', 'localhost')
        self.port = int(os.getenv('PACS_PORT', '11112'))
        self.ae_title = os.getenv('PACS_AE_TITLE', 'MEDICAL_AI')
        self.called_ae_title = os.getenv('PACS_CALLED_AE_TITLE', 'PACS_SERVER')
        self.query_retrieve_level = os.getenv('PACS_QUERY_LEVEL', 'STUDY')
        self.auto_fetch_interval = int(os.getenv('PACS_AUTO_FETCH_INTERVAL', '300'))  # 5 minutes
        self.store_dir = Path(os.getenv('PACS_STORE_DIR', './pacs_storage'))
        self.store_dir.mkdir(parents=True, exist_ok=True)
        
    def is_enabled(self) -> bool:
        return self.enabled and DICOM_AVAILABLE


class PACSIntegration:
    """
    PACS/DICOM Integration Manager
    
    Provides bidirectional communication with hospital PACS:
    - Query for new studies
    - Retrieve DICOM images
    - Send AI predictions back to PACS
    - Monitor for new studies automatically
    """
    
    def __init__(self, config: Optional[PACSConfig] = None):
        self.config = config or PACSConfig()
        self.ae = None
        self.monitoring = False
        self.monitoring_task = None
        
        if self.config.is_enabled():
            self._initialize_ae()
    
    def _initialize_ae(self):
        """Initialize Application Entity for DICOM communication"""
        if not DICOM_AVAILABLE:
            logger.error("pydicom/pynetdicom not installed")
            return
        
        self.ae = AE(ae_title=self.config.ae_title)
        
        # Add supported presentation contexts
        self.ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind)
        self.ae.add_requested_context(PatientRootQueryRetrieveInformationModelMove)
        self.ae.add_requested_context(StudyRootQueryRetrieveInformationModelFind)
        self.ae.add_requested_context(StudyRootQueryRetrieveInformationModelMove)
        
        # Add storage contexts for receiving images
        for context in StoragePresentationContexts:
            self.ae.add_requested_context(context.abstract_syntax)
        
        logger.info(f"PACS AE initialized: {self.config.ae_title}")
    
    def query_studies(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        patient_id: Optional[str] = None,
        study_description: Optional[str] = None,
        modality: Optional[str] = None
    ) -> List[Dict]:
        """
        Query PACS for studies matching criteria
        
        Args:
            start_date: Start of study date range
            end_date: End of study date range
            patient_id: Patient ID to filter
            study_description: Study description to filter
            modality: Modality to filter (e.g., 'CR', 'CT', 'MR')
        
        Returns:
            List of study metadata dictionaries
        """
        if not self.config.is_enabled():
            logger.warning("PACS integration not enabled")
            return []
        
        try:
            # Build query dataset
            ds = pydicom.Dataset()
            ds.QueryRetrieveLevel = 'STUDY'
            ds.StudyInstanceUID = ''
            ds.PatientName = ''
            ds.PatientID = patient_id or ''
            ds.StudyDate = self._format_date_range(start_date, end_date)
            ds.StudyDescription = study_description or ''
            ds.ModalitiesInStudy = modality or ''
            ds.StudyTime = ''
            ds.AccessionNumber = ''
            
            # Perform C-FIND query
            studies = []
            assoc = self.ae.associate(
                self.config.host,
                self.config.port,
                ae_title=self.config.called_ae_title
            )
            
            if assoc.is_established:
                responses = assoc.send_c_find(
                    ds,
                    StudyRootQueryRetrieveInformationModelFind
                )
                
                for (status, identifier) in responses:
                    if status and identifier:
                        study_info = {
                            'study_uid': str(identifier.StudyInstanceUID) if hasattr(identifier, 'StudyInstanceUID') else '',
                            'patient_id': str(identifier.PatientID) if hasattr(identifier, 'PatientID') else '',
                            'patient_name': str(identifier.PatientName) if hasattr(identifier, 'PatientName') else '',
                            'study_date': str(identifier.StudyDate) if hasattr(identifier, 'StudyDate') else '',
                            'study_time': str(identifier.StudyTime) if hasattr(identifier, 'StudyTime') else '',
                            'study_description': str(identifier.StudyDescription) if hasattr(identifier, 'StudyDescription') else '',
                            'modality': str(identifier.ModalitiesInStudy) if hasattr(identifier, 'ModalitiesInStudy') else '',
                            'accession_number': str(identifier.AccessionNumber) if hasattr(identifier, 'AccessionNumber') else '',
                        }
                        studies.append(study_info)
                
                assoc.release()
                logger.info(f"Found {len(studies)} studies in PACS")
            else:
                logger.error(f"Failed to associate with PACS at {self.config.host}:{self.config.port}")
            
            return studies
        
        except Exception as e:
            logger.error(f"Error querying PACS: {e}")
            return []
    
    def retrieve_study(self, study_uid: str) -> Optional[Path]:
        """
        Retrieve DICOM images for a study from PACS
        
        Args:
            study_uid: Study Instance UID
        
        Returns:
            Path to directory containing retrieved DICOM files
        """
        if not self.config.is_enabled():
            logger.warning("PACS integration not enabled")
            return None
        
        try:
            study_dir = self.config.store_dir / study_uid
            study_dir.mkdir(parents=True, exist_ok=True)
            
            # Build C-MOVE request
            ds = pydicom.Dataset()
            ds.QueryRetrieveLevel = 'STUDY'
            ds.StudyInstanceUID = study_uid
            
            # Setup storage SCP to receive images
            handlers = [
                (evt.EVT_C_STORE, self._handle_store, [study_dir])
            ]
            
            # Start storage SCP in background
            scp = self.ae.start_server(
                ('', 11113),
                block=False,
                evt_handlers=handlers
            )
            
            # Perform C-MOVE to trigger transfer
            assoc = self.ae.associate(
                self.config.host,
                self.config.port,
                ae_title=self.config.called_ae_title
            )
            
            if assoc.is_established:
                responses = assoc.send_c_move(
                    ds,
                    self.config.ae_title,  # Destination AE (ourselves)
                    StudyRootQueryRetrieveInformationModelMove
                )
                
                for (status, identifier) in responses:
                    if status:
                        logger.info(f"C-MOVE status: {status.Status}")
                
                assoc.release()
            else:
                logger.error(f"Failed to associate with PACS for C-MOVE")
                scp.shutdown()
                return None
            
            # Wait for transfers to complete
            import time
            time.sleep(2)
            scp.shutdown()
            
            # Check if files were received
            dicom_files = list(study_dir.glob("*.dcm"))
            if dicom_files:
                logger.info(f"Retrieved {len(dicom_files)} DICOM files for study {study_uid}")
                return study_dir
            else:
                logger.warning(f"No DICOM files received for study {study_uid}")
                return None
        
        except Exception as e:
            logger.error(f"Error retrieving study {study_uid}: {e}")
            return None
    
    def _handle_store(self, event, storage_dir):
        """Handle incoming DICOM C-STORE request"""
        ds = event.dataset
        ds.file_meta = event.file_meta
        
        # Generate filename
        filename = f"{ds.SOPInstanceUID}.dcm"
        filepath = storage_dir / filename
        
        # Save DICOM file
        ds.save_as(filepath, write_like_original=False)
        
        return 0x0000  # Success
    
    def send_result_to_pacs(
        self,
        study_uid: str,
        prediction: str,
        confidence: float,
        model_name: str
    ) -> bool:
        """
        Send AI prediction back to PACS as Secondary Capture or Structured Report
        
        Args:
            study_uid: Original study UID
            prediction: AI prediction label
            confidence: Prediction confidence
            model_name: Model that made prediction
        
        Returns:
            True if successful, False otherwise
        """
        if not self.config.is_enabled():
            logger.warning("PACS integration not enabled")
            return False
        
        try:
            # Create DICOM Structured Report with AI results
            ds = pydicom.Dataset()
            
            # Patient/Study information (would need to retrieve from original study)
            ds.StudyInstanceUID = study_uid
            ds.SeriesInstanceUID = pydicom.uid.generate_uid()
            ds.SOPInstanceUID = pydicom.uid.generate_uid()
            ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.88.11'  # Basic Text SR
            
            # AI Result content
            ds.ContentDate = datetime.now().strftime('%Y%m%d')
            ds.ContentTime = datetime.now().strftime('%H%M%S')
            ds.Manufacturer = 'Medical AI System'
            ds.ManufacturerModelName = model_name
            
            # Structured content
            ds.ConceptNameCodeSequence = pydicom.Sequence([self._create_code_item('AI Prediction')])
            ds.TextValue = f"{prediction} (confidence: {confidence:.1%})"
            
            # Send to PACS via C-STORE
            assoc = self.ae.associate(
                self.config.host,
                self.config.port,
                ae_title=self.config.called_ae_title
            )
            
            if assoc.is_established:
                status = assoc.send_c_store(ds)
                assoc.release()
                
                if status:
                    logger.info(f"Successfully sent AI result to PACS for study {study_uid}")
                    return True
                else:
                    logger.error(f"Failed to send AI result to PACS")
                    return False
            else:
                logger.error(f"Failed to associate with PACS for C-STORE")
                return False
        
        except Exception as e:
            logger.error(f"Error sending result to PACS: {e}")
            return False
    
    def _create_code_item(self, text: str) -> pydicom.Dataset:
        """Create DICOM code item"""
        item = pydicom.Dataset()
        item.CodeValue = '1'
        item.CodingSchemeDesignator = 'LOCAL'
        item.CodeMeaning = text
        return item
    
    def _format_date_range(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> str:
        """Format date range for DICOM query"""
        if not start_date and not end_date:
            return ''
        
        start_str = start_date.strftime('%Y%m%d') if start_date else ''
        end_str = end_date.strftime('%Y%m%d') if end_date else ''
        
        if start_str and end_str:
            return f"{start_str}-{end_str}"
        elif start_str:
            return f"{start_str}-"
        elif end_str:
            return f"-{end_str}"
        else:
            return ''
    
    async def start_monitoring(self, callback=None):
        """
        Start automatic monitoring for new studies
        
        Args:
            callback: Async function to call when new studies found
                     Signature: async def callback(studies: List[Dict])
        """
        if not self.config.is_enabled():
            logger.warning("PACS integration not enabled")
            return
        
        if self.monitoring:
            logger.warning("PACS monitoring already running")
            return
        
        self.monitoring = True
        logger.info(f"Starting PACS monitoring (interval: {self.config.auto_fetch_interval}s)")
        
        last_check = datetime.now() - timedelta(hours=1)
        
        while self.monitoring:
            try:
                # Query for studies since last check
                studies = self.query_studies(start_date=last_check)
                
                if studies and callback:
                    await callback(studies)
                
                last_check = datetime.now()
                
                # Wait for next interval
                await asyncio.sleep(self.config.auto_fetch_interval)
            
            except Exception as e:
                logger.error(f"Error in PACS monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def stop_monitoring(self):
        """Stop automatic PACS monitoring"""
        self.monitoring = False
        logger.info("Stopping PACS monitoring")
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to PACS server
        
        Returns:
            (success: bool, message: str)
        """
        if not self.config.is_enabled():
            return False, "PACS integration not enabled"
        
        if not DICOM_AVAILABLE:
            return False, "pydicom/pynetdicom not installed"
        
        try:
            assoc = self.ae.associate(
                self.config.host,
                self.config.port,
                ae_title=self.config.called_ae_title
            )
            
            if assoc.is_established:
                assoc.release()
                return True, f"Successfully connected to PACS at {self.config.host}:{self.config.port}"
            else:
                return False, f"Failed to associate with PACS at {self.config.host}:{self.config.port}"
        
        except Exception as e:
            return False, f"Connection error: {e}"
    
    def extract_image_from_dicom(self, dicom_path: Path) -> Optional[Path]:
        """
        Extract image from DICOM file and save as PNG/JPEG for inference
        
        Args:
            dicom_path: Path to DICOM file
        
        Returns:
            Path to extracted image file
        """
        if not DICOM_AVAILABLE:
            logger.error("pydicom not installed")
            return None
        
        try:
            ds = pydicom.dcmread(dicom_path)
            
            # Get pixel data
            if not hasattr(ds, 'pixel_array'):
                logger.error(f"No pixel data in DICOM file: {dicom_path}")
                return None
            
            pixel_array = ds.pixel_array
            
            # Convert to image
            from PIL import Image
            import numpy as np
            
            # Normalize to 0-255
            pixel_array = pixel_array.astype(float)
            pixel_array = (pixel_array - pixel_array.min()) / (pixel_array.max() - pixel_array.min()) * 255
            pixel_array = pixel_array.astype(np.uint8)
            
            # Create image
            img = Image.fromarray(pixel_array)
            
            # Save as PNG
            output_path = dicom_path.with_suffix('.png')
            img.save(output_path)
            
            logger.info(f"Extracted image from DICOM: {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Error extracting image from DICOM: {e}")
            return None


# Global instance
_pacs_integration = None


def get_pacs_integration() -> PACSIntegration:
    """Get global PACS integration instance"""
    global _pacs_integration
    if _pacs_integration is None:
        _pacs_integration = PACSIntegration()
    return _pacs_integration


# Workflow automation
async def process_new_studies(studies: List[Dict]):
    """
    Automatically process new studies from PACS
    
    This callback is called by the monitoring loop when new studies are found.
    It retrieves images, runs inference, and sends results back.
    """
    from api.model_manager import get_model_manager
    
    pacs = get_pacs_integration()
    model_mgr = get_model_manager()
    
    for study in studies:
        try:
            logger.info(f"Processing study: {study['study_uid']}")
            
            # Retrieve DICOM images
            study_dir = pacs.retrieve_study(study['study_uid'])
            if not study_dir:
                logger.warning(f"Failed to retrieve study {study['study_uid']}")
                continue
            
            # Process each DICOM file
            dicom_files = list(study_dir.glob("*.dcm"))
            for dicom_file in dicom_files:
                # Extract image
                image_path = pacs.extract_image_from_dicom(dicom_file)
                if not image_path:
                    continue
                
                # Determine model based on modality
                modality = study.get('modality', '')
                model_name = _select_model_for_modality(modality)
                
                if not model_name:
                    logger.warning(f"No model found for modality: {modality}")
                    continue
                
                # Run inference
                result = await model_mgr.run_inference(model_name, image_path)
                
                if result:
                    # Send result back to PACS
                    pacs.send_result_to_pacs(
                        study['study_uid'],
                        result['prediction'],
                        result['confidence'],
                        model_name
                    )
                    
                    logger.info(f"Processed {dicom_file.name}: {result['prediction']} ({result['confidence']:.1%})")
        
        except Exception as e:
            logger.error(f"Error processing study {study['study_uid']}: {e}")


def _select_model_for_modality(modality: str) -> Optional[str]:
    """Select appropriate model based on imaging modality"""
    modality_map = {
        'CR': 'pneumonia_detector',  # Chest X-ray
        'DX': 'pneumonia_detector',  # Digital X-ray
        'CT': 'lung_cancer_detector',
        'MR': 'brain_tumor_detector',
        'US': 'breast_cancer_detector',
    }
    return modality_map.get(modality.upper())


if __name__ == '__main__':
    # Test PACS integration
    import asyncio
    
    pacs = get_pacs_integration()
    
    # Test connection
    success, message = pacs.test_connection()
    print(f"Connection test: {message}")
    
    if success:
        # Query recent studies
        studies = pacs.query_studies(
            start_date=datetime.now() - timedelta(days=7)
        )
        print(f"\nFound {len(studies)} studies in last 7 days")
        for study in studies[:5]:
            print(f"  - {study['patient_id']}: {study['study_description']} ({study['study_date']})")
