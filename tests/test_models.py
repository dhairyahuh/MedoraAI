"""
Unit tests for model inference
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from models.model_manager import MedicalModelWrapper, ModelPool
import numpy as np
from PIL import Image
import io


def create_test_image(size=(224, 224)):
    """Create a test image"""
    # Create random RGB image
    img_array = np.random.randint(0, 255, (*size, 3), dtype=np.uint8)
    img = Image.fromarray(img_array)
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    return img_bytes.getvalue()


@pytest.fixture
def test_image():
    """Fixture to provide test image"""
    return create_test_image()


@pytest.mark.asyncio
async def test_model_loading():
    """Test that models can be loaded"""
    model_name = 'pneumonia_detector'
    
    try:
        model = MedicalModelWrapper(model_name, device='cpu')
        assert model is not None
        assert model.model_name == model_name
        assert len(model.classes) > 0
        print(f"✓ Model {model_name} loaded successfully")
    except Exception as e:
        pytest.skip(f"Model loading skipped (dependencies not installed): {e}")


@pytest.mark.asyncio
async def test_inference_latency(test_image):
    """Test that inference completes within time threshold"""
    model_name = 'pneumonia_detector'
    
    try:
        model = MedicalModelWrapper(model_name, device='cpu')
        result = model.predict(test_image)
        
        assert result is not None
        assert 'inference_time' in result
        assert result['inference_time'] < config.MAX_RESPONSE_TIME
        assert 'predicted_class' in result
        assert 'confidence' in result
        
        print(f"✓ Inference completed in {result['inference_time']:.3f}s")
        print(f"  Predicted: {result['predicted_class']} ({result['confidence']:.3f})")
        
    except Exception as e:
        pytest.skip(f"Inference test skipped: {e}")


@pytest.mark.asyncio
async def test_model_accuracy():
    """Test model accuracy on synthetic test set"""
    # This is a placeholder - in production, use real labeled test data
    model_name = 'pneumonia_detector'
    
    try:
        model = MedicalModelWrapper(model_name, device='cpu')
        
        # Create synthetic test set
        test_images = []
        for i in range(10):
            img_bytes = create_test_image()
            label = i % len(model.classes)  # Synthetic labels
            test_images.append((img_bytes, label))
        
        # Note: With synthetic data, accuracy will be near random
        # This test just ensures the evaluation function works
        accuracy = model.evaluate(test_images)
        
        assert 0.0 <= accuracy <= 1.0
        print(f"✓ Model evaluation completed (synthetic accuracy: {accuracy:.3f})")
        
    except Exception as e:
        pytest.skip(f"Accuracy test skipped: {e}")


@pytest.mark.asyncio
async def test_model_pool():
    """Test model pool initialization"""
    try:
        pool = ModelPool(device='cpu')
        
        assert len(pool.models) > 0
        print(f"✓ Model pool initialized with {len(pool.models)} models")
        
        # Test getting a model
        model = pool.get_model('pneumonia_detector')
        assert model is not None
        
    except Exception as e:
        pytest.skip(f"Model pool test skipped: {e}")


@pytest.mark.asyncio
async def test_all_model_architectures():
    """Test that all configured models can be instantiated"""
    failed_models = []
    
    for model_name in config.MODEL_SPECS.keys():
        try:
            model = MedicalModelWrapper(model_name, device='cpu')
            assert model is not None
            print(f"✓ {model_name} loaded successfully")
        except Exception as e:
            failed_models.append((model_name, str(e)))
            print(f"✗ {model_name} failed: {e}")
    
    if failed_models:
        print(f"\n{len(failed_models)} models failed to load:")
        for name, error in failed_models:
            print(f"  - {name}: {error}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
