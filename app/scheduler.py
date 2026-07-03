# app/scheduler.py
"""
Campaign Scheduling Module.
Manages automatic start/stop scheduling for campaigns based on date/time ranges.
"""
import asyncio
from datetime import datetime
from typing import Dict, Any


class CampaignScheduler:
    """
    Scheduler for campaign start/stop automation.
    
    Tracks scheduled time windows and automatically updates campaign status.
    """
    
    def __init__(self):
        self.schedules: Dict[str, Dict] = {}
        self.running = False
    
    def schedule_campaign(
        self, 
        campaign_id: str, 
        start_date: str, 
        end_date: str,
        start_time: str = "00:00", 
        end_time: str = "23:59"
    ) -> bool:
        """
        Schedule a campaign to run within specific date/time windows.
        
        Args:
            campaign_id: Unique campaign identifier
            start_date: Date to start (YYYY-MM-DD format)
            end_date: Date to stop (YYYY-MM-DD format)
            start_time: Start time in 24-hour format (HH:MM)
            end_time: End time in 24-hour format (HH:MM)
        
        Returns:
            True if scheduled successfully
        """
        self.schedules[campaign_id] = {
            "start_date": start_date,
            "end_date": end_date,
            "start_time": start_time,
            "end_time": end_time,
            "active": True,
            "created_at": datetime.now().isoformat()
        }
        return True
    
    def unschedule_campaign(self, campaign_id: str) -> bool:
        """
        Remove schedule for a campaign.
        
        Args:
            campaign_id: Unique campaign identifier
        
        Returns:
            True if unscheduled successfully
        """
        if campaign_id in self.schedules:
            del self.schedules[campaign_id]
            return True
        return False
    
    def get_schedule(self, campaign_id: str) -> Dict:
        """
        Get current schedule for a campaign.
        
        Args:
            campaign_id: Unique campaign identifier
        
        Returns:
            Schedule dictionary or empty dict if not scheduled
        """
        return self.schedules.get(campaign_id, {})
    
    def get_all_schedules(self) -> Dict[str, Dict]:
        """
        Get all active schedules.
        
        Returns:
            Dictionary of all campaigns with their schedules
        """
        return {k: v for k, v in self.schedules.items() if v.get("active", False)}
    
    async def check_and_apply(self, campaigns_store: Dict):
        """
        Check scheduled times and apply status changes to campaigns.
        
        This should be run periodically (e.g., every minute) to update
        campaign statuses based on scheduling rules.
        
        Args:
            campaigns_store: Dictionary of all campaigns in memory
        """
        now = datetime.now()
        today = now.date().isoformat()
        current_time = now.strftime("%H:%M")
        
        for campaign_id, schedule in list(self.schedules.items()):
            if not schedule.get("active", True):
                continue
            
            is_scheduled = True
            
            # Check date range
            if schedule["start_date"] <= today <= schedule["end_date"]:
                if schedule["start_time"] <= current_time <= schedule["end_time"]:
                    # Campaign should be active during this window
                    if campaign_id in campaigns_store:
                        data = campaigns_store[campaign_id]
                        if data.get("status") != "active":
                            data["status"] = "active"
                            campaigns_store[campaign_id] = data
                            print(f"[Scheduler] Campaign {campaign_id} activated")
                else:
                    # Outside daily time window - pause campaign
                    if campaign_id in campaigns_store:
                        data = campaigns_store[campaign_id]
                        if data.get("status") != "paused":
                            data["status"] = "paused"
                            campaigns_store[campaign_id] = data
                            print(f"[Scheduler] Campaign {campaign_id} paused (outside daily hours)")
            else:
                # Outside date range - deactivate
                if campaign_id in campaigns_store:
                    data = campaigns_store[campaign_id]
                    if data.get("status") != "inactive":
                        data["status"] = "inactive"
                        campaigns_store[campaign_id] = data
                        print(f"[Scheduler] Campaign {campaign_id} deactivated (outside date range)")
