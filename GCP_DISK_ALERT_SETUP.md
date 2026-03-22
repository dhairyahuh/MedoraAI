# How to Set Up Disk Space Alerts in Google Cloud (GCP)

Since the **Google Cloud Ops Agent** is already currently running on your VM (`medora`), it is already sending disk usage metrics to GCP. You just need to create an Alerting Policy to notify you when space gets low.

## Step 1: Go to Monitoring
1. Open the [Google Cloud Console](https://console.cloud.google.com).
2. In the search bar, type **"Monitoring"** and select **Monitoring**.
3. In the left (hamburger) menu, click **Detect** > **Alerting**.

## Step 2: Create a New Alert Policy
1. Click **+ CREATE POLICY**.
2. Click **Select a metric**.
3. Uncheck "Active" to see all metrics if needed, then search for **"disk/percent_used"**.
   - Resource Type: `VM Instance`
   - Metric Category: `Agent` > `disk`
   - Metric: `percent_used`
4. Click **Apply**.

## Step 3: Configure the Trigger
1. **Rolling window**: Select `1 min`.
2. **Rolling window function**: Select `Mean` (average).
3. Click **Next** to configure the trigger condition.
4. **Condition type**: `Threshold`.
5. **Alert trigger**: `Any time series violates`.
6. **Threshold position**: `Above threshold`.
7. **Threshold value**: `85` (This means alert when disk is >85% full).
   - *Note: 85% of 30GB leaves ~4.5GB free, which gives you time to react.*

## Step 4: Set Notifications
1. Click **Next** to "Who should be notified?".
2. Click **Manage Notification Channels**.
3. Add your **Email** (or SMS/Slack if supported).
4. Return to the alert setup tab and **select the checkbox** for your email channel.
5. Click **OK**.

## Step 5: Name and Finish
1. **Alert name**: `VM Disk Space Warning (>85%)`
2. **Documentation**: "The VM is running out of space. Run `df -h` to check usage and clear `federated_data/gradients`."
3. Click **Create Policy**.

---

## Alternative: Auto-Cleanup (Cron Job)
If you want the server to *automatically* clean itself instead of just warning you, we can set up a daily task to delete old gradient files.

**Command to add a daily cleanup job:**

```bash
# Delete gradient files older than 1 day every midnight
(crontab -l 2>/dev/null; echo "0 0 * * * find /var/www/medora/federated_data/gradients -name '*.pt' -mtime +1 -delete") | crontab -
```
