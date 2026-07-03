# 🧪 Phase 3 Testing & Verification Guide

## Overview
All backend endpoints and UI components for Phase 3 features have been implemented. This guide walks through testing each feature systematically.

---

## Quick Start

### Step 1: Start the Application

```bash
cd D:\marketing-agents
docker-compose up -d --build
```

Wait ~30 seconds for the application to start, then verify it's running:

```bash
curl http://localhost:8000/health || echo "Health endpoint not available"
```

---

## Testing Checklist

### ✅ 1. Authentication & Login (Required First)

**Task**: Get a valid token for subsequent API calls

**How to Test**:
```bash
# Login as admin (or any user with password in .env)
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "YourPassword123"
  }'

# Save the token for use in subsequent requests
# Example: TOKEN="YourTokenHere"
```

**Expected Response**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "...",
    "email": "admin@example.com",
    "full_name": "Admin User",
    "role": "admin"
  }
}
```

---

### ✅ 2. Analytics Endpoints (New Phase 3 Features)

#### 2a. Get Analytics for All Campaigns

**Endpoint**: `GET /api/analytics/all`

```bash
curl -X GET "http://localhost:8000/api/analytics/all" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "campaigns": [
    {
      "campaign_id": "...",
      "name": "Campaign Name",
      "status": "active",
      "metrics": {...},
      "creatives_count": {
        "google": 3,
        "meta": 2
      }
    }
  ],
  "aggregated": {
    "total_impressions": 15000,
    "total_clicks": 750,
    "total_spend": 45.67,
    "avg_ctr": 5.0,
    "campaign_count": 2
  }
}
```

**What to Verify**:
- ✅ Response includes campaigns array
- ✅ Aggregated metrics are calculated correctly
- ✅ Each campaign has proper structure

---

#### 2b. Get Analytics for Single Campaign

**Endpoint**: `GET /api/analytics/{campaign_id}?days=N`

```bash
# Test with 30 days of data
curl -X GET "http://localhost:8000/api/analytics/YOUR_CAMPAIGN_ID?days=30" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "campaign_id": "...",
  "daily": [
    {
      "date": "2024-01-01",
      "impressions": 1500,
      "clicks": 75,
      "ctr": 5.0,
      "spend": 35.50
    },
    {
      "date": "2024-01-02",
      "impressions": 1800,
      "clicks": 90,
      "ctr": 5.0,
      "spend": 42.30
    }
  ],
  "summary": {
    "status": "active",
    "created_at": "...",
    "total_spend": 1234.56,
    "avg_ctr": 4.87,
    "trend": "increasing"
  }
}
```

**What to Verify**:
- ✅ Daily data array has correct structure
- ✅ Trend field shows "increasing", "decreasing", or "stable"
- ✅ Summary metrics match daily data calculations

---

### ✅ 3. Campaign Scheduling (New Phase 3 Feature)

#### 3a. Schedule a Campaign

**Endpoint**: `POST /api/campaigns/{campaign_id}/schedule`

```bash
curl -X POST "http://localhost:8000/api/campaigns/YOUR_CAMPAIGN_ID/schedule" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-12-01",
    "end_date": "2024-12-31",
    "start_time": "09:00",
    "end_time": "18:00"
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "campaign_id": "YOUR_CAMPAIGN_ID"
}
```

**What to Verify**:
- ✅ Returns success: true
- ✅ Works for admin and client_manager roles only (require_role decorator)

---

#### 3b. Get Schedule Status

**Endpoint**: `GET /api/campaigns/{campaign_id}/schedule`

```bash
curl -X GET "http://localhost:8000/api/campaigns/YOUR_CAMPAIGN_ID/schedule" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "start_date": "2024-12-01",
  "end_date": "2024-12-31",
  "start_time": "09:00",
  "end_time": "18:00",
  "active": true,
  "created_at": "2024-11-15T10:30:00.000Z"
}
```

**What to Verify**:
- ✅ Schedule exists after POST
- ✅ All fields are populated correctly

---

#### 3c. Unschedule a Campaign

**Endpoint**: `DELETE /api/campaigns/{campaign_id}/schedule`

```bash
curl -X DELETE "http://localhost:8000/api/campaigns/YOUR_CAMPAIGN_ID/schedule" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "success": true,
  "campaign_id": "YOUR_CAMPAIGN_ID"
}
```

**What to Verify**:
- ✅ Returns success: true
- ✅ Schedule is removed (verify with GET /api/campaigns/{id}/schedule)

---

### ✅ 4. Campaign Delete (P2 Feature - Verify Still Works)

**Endpoint**: `DELETE /api/campaigns/{campaign_id}`

```bash
curl -X DELETE "http://localhost:8000/api/campaigns/YOUR_CAMPAIGN_ID" \
  -H "Authorization: Bearer TOKEN"
```

**Expected Response**:
```json
{
  "message": "Campaign YOUR_CAMPAIGN_ID deleted successfully"
}
```

**What to Verify**:
- ✅ Campaign removed from database and memory
- ✅ Optimization history also deleted
- ✅ UI refreshes campaign list

---

### ✅ 5. PDF Report Generation (P2 Feature - Verify Still Works)

**Endpoint**: `GET /api/campaigns/{campaign_id}/report`

```bash
curl -X GET "http://localhost:8000/api/campaigns/YOUR_CAMPAIGN_ID/report" \
  -H "Authorization: Bearer TOKEN" \
  --output report.pdf
```

**What to Verify**:
- ✅ File downloaded as PDF
- ✅ Opens without font errors
- ✅ Contains campaign name, KPI table, recommendations

---

### ✅ 6. A/B Testing (P2 Feature - Verify Still Works)

**Endpoint**: `POST /api/campaigns/{campaign_id}/ab-test`

```bash
# First get creatives to extract Google Ads
curl -X GET "http://localhost:8000/api/campaigns/YOUR_CAMPAIGN_ID/creatives" \
  -H "Authorization: Bearer TOKEN"

# Then create A/B test with variants from response
```

**What to Verify**:
- ✅ Creates test when 2+ Google Ads exist
- ✅ Shows "running" status during processing
- ✅ Promotes winner button appears when completed

---

## Browser Testing (Dashboard UI)

### 6a. Open the Dashboard

Navigate to: `http://localhost:8000`

**Verify You Can See**:
- ✅ Login page (if not authenticated)
- ✅ Dashboard after login
- ✅ Sidebar navigation includes "Analytics" link

---

### 6b. Navigate to Analytics Section

Click "Analytics" in sidebar or check for analytics dashboard content.

**Expected Behavior**:
- ✅ Shows campaign selector dropdown
- ✅ Shows day range selector (7/30/90 days)
- ✅ Summary cards display metrics
- ✅ Charts render with Chart.js

---

### 6c. Test Chart Rendering

After selecting a campaign and clicking the selector:

**Expected Behavior**:
- ✅ Impressions & Clicks line chart displays correctly
- ✅ CTR trend line chart displays correctly
- ✅ Legend shows correct labels
- ✅ Data points match API response

---

## Troubleshooting

### Issue: Analytics endpoint returns 404

**Possible Causes**:
1. Campaign doesn't exist - create one first via onboard
2. Endpoints need app restart after code changes

**Solution**:
```bash
# Stop and rebuild the app
docker-compose down
docker-compose up -d --build
```

---

### Issue: Chart.js not rendering

**Check Console for Errors**:
1. Open browser DevTools (F12)
2. Check Console tab for errors
3. Verify Chart.js CDN loaded correctly

**Solution**:
- Ensure `<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>` is in HTML head
- Clear browser cache and refresh

---

### Issue: Authentication errors (401/403)

**Verify Token Format**:
```bash
# Check token in Authorization header
curl -v http://localhost:8000/api/campaigns \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Headers**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

---

### Issue: "Campaign not found" errors

**Verify Campaign Exists**:
```bash
curl -X GET "http://localhost:8000/api/campaigns" \
  -H "Authorization: Bearer TOKEN"
```

If empty, create a new campaign via onboard endpoint or dashboard.

---

## Testing Results Template

Fill this out after running tests:

| Feature | Endpoint/URL | Status (✅/❌) | Notes |
|---------|---------------|----------------|-------|
| Analytics All | GET /api/analytics/all | ☐ | |
| Analytics Single | GET /api/analytics/{id} | ☐ | |
| Schedule Campaign | POST /api/campaigns/{id}/schedule | ☐ | |
| Get Schedule | GET /api/campaigns/{id}/schedule | ☐ | |
| Unschedule | DELETE /api/campaigns/{id}/schedule | ☐ | |
| Delete Campaign | DELETE /api/campaigns/{id} | ☐ | |
| PDF Report | GET /api/campaigns/{id}/report | ☐ | |
| A/B Testing | POST /api/campaigns/{id}/ab-test | ☐ | |

---

## Environment Variables for Alerts

To enable email/Slack alerts, add to `.env`:

```bash
# Email Alerts
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_RECIPIENTS=admin@example.com,manager@example.com

# Slack Alerts (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Alert Thresholds (default: use environment values or these)
ALERT_CTR_THRESHOLD=1.0
ALERT_ROAS_THRESHOLD=1.2
ALERT_CPC_THRESHOLD=3.0
```

Restart app after updating `.env`:

```bash
docker-compose restart app
```

---

## Production Deployment Checklist

- [ ] All endpoints return correct responses
- [ ] Authentication works correctly (401/403 errors handled)
- [ ] Charts render properly in browser
- [ ] Analytics data loads for all campaigns
- [ ] Scheduling triggers at correct times (every minute)
- [ ] Alerts configured and tested (optional)
- [ ] Multi-tenancy working (non-admin users see only their campaigns)

---

## Next Steps After Testing

1. **If all tests pass**: Deploy to production
2. **If some features fail**: Review error messages, check logs (`docker-compose logs app`)
3. **Optional enhancements**:
   - Add branded reports UI button
   - Implement real KPI fetching (not simulated data)
   - Add performance alerts testing

---

## Support & Debugging

### Check Application Logs
```bash
docker-compose logs -f app
```

### View Database Schema
```sql
sqlite3 marketing_agents.db ".schema"
```

### Test Database Directly
```bash
docker exec marketing-postgres psql -U postgres -c "SELECT * FROM clients;"
```

---

## Contact for Help

If you encounter issues:
1. Check this testing guide
2. Review application logs
3. Verify environment variables (`.env` file)
4. Ensure all dependencies installed (`pip install -r requirements.txt`)

---

**Last Updated**: $(date +%Y-%m-%d)  
**Phase 3 Status**: ✅ Backend Complete, UI Components Ready for Testing
