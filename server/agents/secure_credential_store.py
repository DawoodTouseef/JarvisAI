"""Secure credential and personal data storage for browser automation"""

from typing import Dict, Any, Optional, List
from mongita import MongitaClientMemory
import logging


class SecureCredentialStore:
    """Secure credential and personal data storage using Mongita in-memory database"""
    
    def __init__(self, db_path: str = "secure_browser_db"):
        """
        Initialize the credential store
        
        Args:
            db_path: Database name for Mongita
        """
        self.client = MongitaClientMemory()
        self.db = self.client[db_path]
        self.credentials = self.db.credentials
        self.addresses = self.db.addresses
        self.personal_info = self.db.personal_info
        self.social_accounts = self.db.social_accounts
        self.preferences = self.db.preferences
        self.logger = logging.getLogger(__name__)
    
    def add_credential(self, site: str, username: str, password: str, **kwargs):
        """
        Store login credentials securely
        
        Args:
            site: Website domain (e.g., 'youtube.com', 'gmail.com')
            username: Username or email
            password: Password
            **kwargs: Additional metadata
        """
        doc = {
            "site": site.lower(),
            "username": username,
            "password": password,
            "metadata": kwargs
        }
        # Check if exists, then update or insert (Mongita doesn't support upsert)
        existing = self.credentials.find_one({"site": site.lower()})
        if existing:
            self.credentials.update_one({"site": site.lower()}, {"$set": doc})
        else:
            self.credentials.insert_one(doc)
        self.logger.info(f"✓ Credentials stored for {site}")
    
    def get_credential(self, site: str) -> Optional[Dict]:
        """
        Retrieve credentials with flexible matching
        
        Args:
            site: Website domain to search for
            
        Returns:
            Dictionary with username, password, and site, or None if not found
        """
        # Direct match first
        result = self.credentials.find_one({"site": site.lower()})
        
        if not result:
            # Fuzzy match - try to match partial domain names
            all_creds = list(self.credentials.find({}))
            for cred in all_creds:
                site_name = cred['site'].replace('.com', '').replace('.org', '').replace('.net', '')
                query_name = site.lower().replace('.com', '').replace('.org', '').replace('.net', '')
                if site_name in query_name or query_name in site_name:
                    result = cred
                    break
        
        if result:
            return {
                "username": result["username"],
                "password": result["password"],
                "site": result["site"]
            }
        return None
    
    def prompt_for_credential(self, site: str) -> Optional[Dict]:
        """
        Interactive credential prompt (for CLI usage)
        
        Args:
            site: Website requiring credentials
            
        Returns:
            Dictionary with credentials or None if cancelled
        """
        self.logger.info(f"\n🔐 Credentials needed for {site}")
        print(f"\n🔐 Credentials needed for {site}")
        username = input(f"   Username/Email: ").strip()
        password = input(f"   Password: ").strip()
        
        if username and password:
            self.add_credential(site, username, password)
            print(f"✅ Saved! Will auto-login to {site} in the future")
            return {"username": username, "password": password, "site": site}
        return None
    
    def add_social_account(self, platform: str, username: str, password: str, 
                          profile_name: str = "", **kwargs):
        """
        Store social media account info
        
        Args:
            platform: Social media platform (instagram, twitter, facebook, etc.)
            username: Username or email
            password: Password
            profile_name: Display name or profile name
            **kwargs: Additional metadata
        """
        doc = {
            "platform": platform.lower(),
            "username": username,
            "password": password,
            "profile_name": profile_name,
            "metadata": kwargs
        }
        # Check if exists, then update or insert (Mongita doesn't support upsert)
        existing = self.social_accounts.find_one({"platform": platform.lower()})
        if existing:
            self.social_accounts.update_one({"platform": platform.lower()}, {"$set": doc})
        else:
            self.social_accounts.insert_one(doc)
        self.logger.info(f"✓ {platform} account stored")
    
    def get_social_account(self, platform: str) -> Optional[Dict]:
        """
        Retrieve social media credentials
        
        Args:
            platform: Social media platform name
            
        Returns:
            Dictionary with account info or None if not found
        """
        result = self.social_accounts.find_one({"platform": platform.lower()})
        if result:
            return {
                "username": result["username"],
                "password": result["password"],
                "profile_name": result.get("profile_name", ""),
                "platform": result["platform"]
            }
        return None
    
    def add_personal_info(self, key: str, value: Any):
        """
        Store any personal information
        
        Args:
            key: Information key (e.g., 'full_name', 'email', 'phone')
            value: Information value
        """
        doc = {"key": key.lower(), "value": value}
        # Check if exists, then update or insert (Mongita doesn't support upsert)
        existing = self.personal_info.find_one({"key": key.lower()})
        if existing:
            self.personal_info.update_one({"key": key.lower()}, {"$set": doc})
        else:
            self.personal_info.insert_one(doc)
        self.logger.info(f"✓ {key} stored")
    
    def get_personal_info(self, key: str) -> Optional[Any]:
        """
        Retrieve personal information
        
        Args:
            key: Information key to retrieve
            
        Returns:
            Stored value or None if not found
        """
        result = self.personal_info.find_one({"key": key.lower()})
        return result["value"] if result else None
    
    def list_all_sites(self) -> List[str]:
        """
        List all stored credential sites
        
        Returns:
            List of site domains
        """
        return [doc["site"] for doc in self.credentials.find({})]
    
    def list_social_accounts(self) -> List[str]:
        """
        List all social media accounts
        
        Returns:
            List of platform names
        """
        return [doc["platform"] for doc in self.social_accounts.find({})]
    
    def delete_credential(self, site: str) -> bool:
        """
        Delete stored credentials for a site
        
        Args:
            site: Website domain
            
        Returns:
            True if deleted, False if not found
        """
        result = self.credentials.delete_one({"site": site.lower()})
        if result.deleted_count > 0:
            self.logger.info(f"✓ Credentials deleted for {site}")
            return True
        return False
    
    def delete_social_account(self, platform: str) -> bool:
        """
        Delete stored social media account
        
        Args:
            platform: Social media platform name
            
        Returns:
            True if deleted, False if not found
        """
        result = self.social_accounts.delete_one({"platform": platform.lower()})
        if result.deleted_count > 0:
            self.logger.info(f"✓ {platform} account deleted")
            return True
        return False
    
    def clear_all_credentials(self):
        """Clear all stored credentials (use with caution)"""
        self.credentials.delete_many({})
        self.social_accounts.delete_many({})
        self.personal_info.delete_many({})
        self.logger.warning("⚠️  All credentials cleared")
