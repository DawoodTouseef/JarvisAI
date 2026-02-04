"""Comprehensive tool suite for browser automation operations"""

import os
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
import logging

from browser_use import Tools, ActionResult, BrowserSession
from browser_use.llm.openai.chat import ChatOpenAI
from .secure_credential_store import SecureCredentialStore


class UniversalBrowserTools:
    """Comprehensive tool suite for all browser operations"""
    
    def __init__(self, credential_store: SecureCredentialStore, browser, llm=None):
        """
        Initialize browser tools with credential store
        
        Args:
            credential_store: SecureCredentialStore instance for credential management
            browser: Browser instance
            llm: LLM instance for natural language element selection (optional)
        """
        self.store = credential_store
        self.tools = Tools()
        self.download_dir = Path.home() / "Downloads" / "browser_agent"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.browser = browser
        self.llm = llm
        self._register_tools()
    
    def _register_tools(self):
        """Register all browser automation tools"""
        
        # ==================== NAVIGATION TOOLS ====================
        
        @self.tools.action('Navigate to a website URL')
        async def navigate_to_url(url: str, browser_session: BrowserSession) -> ActionResult:
            """
            Navigate to a specific URL in the browser.
            
            Args:
                url: The URL to navigate to (e.g., 'https://gmail.com', 'https://youtube.com')
            """
            try:
                self.logger.info(f"🌐 Navigating to {url}...")
                
                # Ensure URL has proper protocol
                if not url.startswith('http'):
                    url = f"https://{url}"
                
                page = await browser_session.browser.get_current_page()
                await page.goto(url)
                await asyncio.sleep(3)  # Wait for page to load
                
                return ActionResult(
                    extracted_content=f"Successfully navigated to {url}",
                    include_in_memory=True
                )
            except Exception as e:
                self.logger.error(f"Navigation error: {e}")
                return ActionResult(
                    error=f"Failed to navigate to {url}: {str(e)}",
                    include_in_memory=True
                )
        
        @self.tools.action('Click on an element by natural language description')
        async def click_element(description: str, browser_session: BrowserSession) -> ActionResult:
            """
            Find and click an element on the page using natural language description.
            
            Args:
                description: Natural language description of what to click (e.g., 'login button', 'next page arrow')
            """
            try:
                self.logger.info(f"🖱️  Clicking: {description}...")
                page = await browser_session.browser.get_current_page()
                
                element = await page.get_element_by_prompt(description, llm=self.llm)
                
                if element:
                    await element.click()
                    await asyncio.sleep(1)
                    return ActionResult(
                        extracted_content=f"Successfully clicked on {description}",
                        include_in_memory=True
                    )
                else:
                    return ActionResult(
                        extracted_content=f"Could not find {description} to click",
                        include_in_memory=True
                    )
            except Exception as e:
                self.logger.error(f"Click error: {e}")
                return ActionResult(
                    error=f"Error clicking {description}: {str(e)}",
                    include_in_memory=True
                )
        
        @self.tools.action('Get current page URL and title')
        async def get_page_info(browser_session: BrowserSession) -> ActionResult:
            """Get the current page URL and title"""
            try:
                page = await browser_session.browser.get_current_page()
                url = page.url
                title = await page.get_title()
                
                return ActionResult(
                    extracted_content=f"Current page: {title} ({url})",
                    include_in_memory=True
                )
            except Exception as e:
                self.logger.error(f"Error getting page info: {e}")
                return ActionResult(error=f"Error getting page info: {str(e)}")
        
        # ==================== AUTHENTICATION TOOLS ====================
        
        @self.tools.action('Login to any website using stored credentials. Never ask user for passwords.')
        async def secure_login(website: str, browser_session: BrowserSession) -> ActionResult:
            """
            Securely login to any website. Credentials are retrieved from local database
            and auto-filled without exposing them to the AI.
            
            Args:
                website: Website domain (e.g., 'youtube.com', 'gmail.com', 'instagram.com')
            """
            self.logger.info(f"🔐 Logging into {website}...")
            
            cred = self.store.get_credential(website)
            if not cred:
                return ActionResult(
                    extracted_content=f"No credentials found for {website}. Please add credentials first.",
                    include_in_memory=True
                )
            
            try:
                page = await browser_session.browser.get_current_page()
                
                # Wait for login form to appear
                await asyncio.sleep(2)
                
                # Auto-fill login credentials
                success = await self._auto_fill_login(page, cred, self.llm)
                
                if not success:
                    return ActionResult(
                        extracted_content=f"Could not fill login form for {website}. Please check the page structure.",
                        include_in_memory=True
                    )
                
                # Look for and click submit button
                await asyncio.sleep(1)
                try:
                    submit_button = await page.get_element_by_prompt(
                        "login or sign in button to submit the form",
                        llm=self.llm
                    )
                    if submit_button:
                        await submit_button.click()
                        await asyncio.sleep(3)  # Wait for login to complete
                        
                        return ActionResult(
                            extracted_content=f"Successfully logged into {website}",
                            include_in_memory=True
                        )
                except Exception as e:
                    self.logger.warning(f"Could not find submit button: {e}")
                
                return ActionResult(
                    extracted_content=f"Credentials filled for {website}. Could not locate submit button.",
                    include_in_memory=True
                )
                
            except Exception as e:
                self.logger.error(f"Login error for {website}: {e}", exc_info=True)
                return ActionResult(
                    error=f"Login failed for {website}: {str(e)}",
                    include_in_memory=True
                )
        
        @self.tools.action('Login to social media (Instagram, Twitter, Facebook, LinkedIn, etc.)')
        async def social_login(platform: str, browser_session: BrowserSession) -> ActionResult:
            """
            Login to social media platforms with stored credentials.
            
            Args:
                platform: Social platform name (instagram, twitter, facebook, linkedin, tiktok)
            """
            self.logger.info(f"📱 Logging into {platform}...")
            
            account = self.store.get_social_account(platform)
            if not account:
                return ActionResult(
                    extracted_content=f"No {platform} account found. Please add account first.",
                    include_in_memory=True
                )
            
            try:
                page = await browser_session.browser.get_current_page()
                await asyncio.sleep(2)
                
                success = await self._auto_fill_login(page, account, self.llm)
                
                if success:
                    await asyncio.sleep(1)
                    try:
                        submit_button = await page.get_element_by_prompt(
                            f"login or sign in button on {platform}",
                            llm=self.llm
                        )
                        if submit_button:
                            await submit_button.click()
                            await asyncio.sleep(3)
                    except:
                        pass
                    
                    return ActionResult(
                        extracted_content=f"Logged into {platform} as {account.get('profile_name', account['username'])}",
                        include_in_memory=True
                    )
                else:
                    return ActionResult(
                        extracted_content=f"Could not fill login form for {platform}",
                        include_in_memory=True
                    )
            except Exception as e:
                self.logger.error(f"Social login error: {e}", exc_info=True)
                return ActionResult(
                    error=f"Failed to login to {platform}: {str(e)}",
                    include_in_memory=True
                )
        
        # ==================== CONTENT INTERACTION TOOLS ====================
        
        @self.tools.action('Type or write text content into any field (posts, comments, emails, forms)')
        async def write_content(text: str, field_description: str, browser_session: BrowserSession) -> ActionResult:
            """
            Type text into any input field, textarea, or content editor.
            Works for: social media posts, comments, emails, blog posts, forms, messages, etc.
            
            Args:
                text: The content to write
                field_description: Description of where to write (e.g., "post text area", "email body", "comment box")
            """
            self.logger.info(f"✍️  Writing content to {field_description}...")
            
            page = await browser_session.browser.get_current_page()
            
            try:
                # Use natural language to find the element
                element = await page.get_element_by_prompt(
                    field_description,
                    llm=self.llm
                )
                
                if element:
                    await element.click()
                    await asyncio.sleep(0.5)
                    
                    # Try filling directly
                    try:
                        await element.fill(text)
                    except:
                        # Fallback to typing
                        await page.keyboard.type(text)
                    
                    await asyncio.sleep(0.5)
                    return ActionResult(
                        extracted_content=f"Successfully wrote content to {field_description}",
                        include_in_memory=True
                    )
            except Exception as e:
                self.logger.error(f"Error writing content: {e}")
            
            return ActionResult(
                extracted_content=f"Could not locate {field_description}. Please try again.",
                include_in_memory=True
            )
        
        @self.tools.action('Upload file to any website (profile pictures, documents, images, videos)')
        async def upload_file(file_path: str, browser_session: BrowserSession) -> ActionResult:
            """
            Upload a file from the local system to any upload field.
            
            Args:
                file_path: Full path to the file to upload
            """
            self.logger.info(f"📤 Uploading file: {file_path}")
            
            if not os.path.exists(file_path):
                return ActionResult(
                    error=f"File not found: {file_path}",
                    include_in_memory=True
                )
            
            page = await browser_session.browser.get_current_page()
            
            try:
                # Find file input using natural language
                file_input = await page.get_element_by_prompt(
                    "file upload input or button",
                    llm=self.llm
                )
                
                if file_input:
                    await file_input.set_input_files(file_path)
                    await asyncio.sleep(1)
                    return ActionResult(
                        extracted_content=f"File uploaded: {os.path.basename(file_path)}",
                        include_in_memory=True
                    )
            except Exception as e:
                self.logger.error(f"Upload error: {e}")
                return ActionResult(
                    extracted_content=f"Could not locate upload field. Error: {str(e)}",
                    include_in_memory=True
                )
        
        @self.tools.action('Download files, images, videos, or documents from any website')
        async def download_file(file_description: str, browser_session: BrowserSession) -> ActionResult:
            """
            Initiate file download. Works with download buttons, links, or right-click save.
            
            Args:
                file_description: What to download (e.g., "the PDF file", "profile image", "video")
            """
            self.logger.info(f"⬇️  Initiating download: {file_description}")
            
            return ActionResult(
                extracted_content=f"Ready to download {file_description}. Click the download button or link. Files will be saved to {self.download_dir}",
                include_in_memory=True
            )
        
        # ==================== MEDIA & PLAYBACK TOOLS ====================
        
        @self.tools.action('Play, pause, or control video/audio playback (YouTube, Spotify, Netflix, etc.)')
        async def control_media(action: str, browser_session: BrowserSession) -> ActionResult:
            """
            Control media playback on any website.
            
            Args:
                action: Media control action (play, pause, mute, unmute, fullscreen, seek)
            """
            self.logger.info(f"🎬 Media control: {action}")
            
            page = await browser_session.browser.get_current_page()
            
            # Execute JavaScript to control media
            js_actions = {
                "play": "document.querySelector('video, audio')?.play()",
                "pause": "document.querySelector('video, audio')?.pause()",
                "mute": "document.querySelector('video, audio').muted = true",
                "unmute": "document.querySelector('video, audio').muted = false",
                "fullscreen": "document.querySelector('video')?.requestFullscreen()",
            }
            
            if action.lower() in js_actions:
                try:
                    await page.evaluate(js_actions[action.lower()])
                    return ActionResult(
                        extracted_content=f"Media {action} executed",
                        include_in_memory=True
                    )
                except:
                    pass
            
            return ActionResult(
                extracted_content=f"Attempting to {action} media. You may need to click the media control button.",
                include_in_memory=True
            )
        
        # ==================== SOCIAL MEDIA TOOLS ====================
        
        @self.tools.action('Post content to social media (Instagram, Twitter, Facebook, LinkedIn)')
        async def post_to_social(platform: str, content: str, browser_session: BrowserSession) -> ActionResult:
            """
            Create and publish a post on social media.
            
            Args:
                platform: Social media platform
                content: Post content/caption
            """
            self.logger.info(f"📱 Posting to {platform}...")
            
            page = await browser_session.browser.get_current_page()
            
            try:
                # Find post creation field using natural language
                post_field = await page.get_element_by_prompt(
                    f"post creation area or text box to write a new post on {platform}",
                    llm=self.llm
                )
                
                if post_field:
                    await post_field.click()
                    await asyncio.sleep(1)
                    await post_field.fill(content)
                    await asyncio.sleep(1)
                    
                    return ActionResult(
                        extracted_content=f"Post content written. Now click the 'Post' or 'Share' button to publish.",
                        include_in_memory=True
                    )
            except Exception as e:
                self.logger.error(f"Error posting to {platform}: {e}")
            
            return ActionResult(
                extracted_content=f"Ready to post on {platform}. Locate the post creation area first.",
                include_in_memory=True
            )
        
        @self.tools.action('Like, comment, or interact with social media content')
        async def social_interact(action: str, content: str, browser_session: BrowserSession) -> ActionResult:
            """
            Interact with social media posts.
            
            Args:
                action: Type of interaction (like, comment, share, follow, retweet)
                content: Comment text if action is 'comment', otherwise empty
            """
            self.logger.info(f"👍 Social interaction: {action}")
            
            page = await browser_session.browser.get_current_page()
            
            if action.lower() == "comment" and content:
                try:
                    # Find comment box using natural language
                    comment_field = await page.get_element_by_prompt(
                        "comment input field or text box",
                        llm=self.llm
                    )
                    
                    if comment_field:
                        await comment_field.click()
                        await asyncio.sleep(0.5)
                        await comment_field.fill(content)
                        return ActionResult(
                            extracted_content=f"Comment written: '{content}'. Now submit it.",
                            include_in_memory=True
                        )
                except Exception as e:
                    self.logger.error(f"Error creating comment: {e}")
            else:
                try:
                    # Find action button (like, share, follow, etc.) using natural language
                    action_button = await page.get_element_by_prompt(
                        f"{action} button",
                        llm=self.llm
                    )
                    
                    if action_button:
                        await action_button.click()
                        await asyncio.sleep(1)
                        return ActionResult(
                            extracted_content=f"Successfully {action}d",
                            include_in_memory=True
                        )
                except Exception as e:
                    self.logger.error(f"Error performing {action}: {e}")
            
            return ActionResult(
                extracted_content=f"Ready to {action}. Could not locate the button automatically.",
                include_in_memory=True
            )
        
        # ==================== UTILITY TOOLS ====================
        
        @self.tools.action('Fill a form field with text using natural language description')
        async def fill_form_field(field_description: str, value: str, browser_session: BrowserSession) -> ActionResult:
            """
            Find and fill a specific form field with text.
            
            Args:
                field_description: Natural language description of the field (e.g., 'email input', 'password field')
                value: The value to enter in the field
            """
            try:
                self.logger.info(f"📝 Filling field: {field_description} with value")
                page = await browser_session.browser.get_current_page()
                
                field = await page.get_element_by_prompt(
                    f"{field_description} to fill with text",
                    llm=self.llm
                )
                
                if field:
                    await field.click()
                    await asyncio.sleep(0.3)
                    await field.fill(value)
                    await asyncio.sleep(0.3)
                    
                    return ActionResult(
                        extracted_content=f"Successfully filled {field_description}",
                        include_in_memory=True
                    )
                else:
                    return ActionResult(
                        extracted_content=f"Could not find {field_description}",
                        include_in_memory=True
                    )
            except Exception as e:
                self.logger.error(f"Error filling form field: {e}")
                return ActionResult(error=f"Error filling field: {str(e)}")
        
        @self.tools.action('Press a keyboard key or key combination')
        async def press_key(key: str, browser_session: BrowserSession) -> ActionResult:
            """
            Press a keyboard key or key combination.
            
            Args:
                key: Key to press (e.g., 'Enter', 'Tab', 'Escape', 'Control+A')
            """
            try:
                self.logger.info(f"⌨️  Pressing key: {key}")
                page = await browser_session.browser.get_current_page()
                
                # Map key names
                key_map = {
                    'enter': 'Enter',
                    'return': 'Enter',
                    'tab': 'Tab',
                    'escape': 'Escape',
                    'backspace': 'Backspace',
                    'delete': 'Delete',
                    'space': ' ',
                }
                
                key_to_press = key_map.get(key.lower(), key)
                await page.keyboard.press(key_to_press)
                await asyncio.sleep(0.5)
                
                return ActionResult(
                    extracted_content=f"Pressed {key}",
                    include_in_memory=True
                )
            except Exception as e:
                self.logger.error(f"Error pressing key: {e}")
                return ActionResult(error=f"Error pressing key: {str(e)}")
        
        @self.tools.action('Type or write text content into any field (posts, comments, emails, forms)')
        async def take_screenshot(description: str, browser_session: BrowserSession) -> ActionResult:
            """
            Capture screenshot.
            
            Args:
                description: What to capture (e.g., "full page", "profile section")
            """
            self.logger.info(f"📸 Taking screenshot: {description}")
            
            page = await browser_session.browser.get_current_page()
            
            try:
                screenshot_path = self.download_dir / f"screenshot_{int(asyncio.get_event_loop().time())}.png"
                await page.screenshot(path=str(screenshot_path))
                
                return ActionResult(
                    extracted_content=f"Screenshot saved: {screenshot_path}",
                    include_in_memory=True
                )
            except Exception as e:
                return ActionResult(error=f"Screenshot failed: {str(e)}")
        
        @self.tools.action('Wait for page to load or specific element to appear')
        async def wait_for_element(description: str, seconds: int, browser_session: BrowserSession) -> ActionResult:
            """
            Wait for page elements to load.
            
            Args:
                description: What to wait for
                seconds: How long to wait (max 30 seconds)
            """
            wait_time = min(seconds, 30)
            self.logger.info(f"⏳ Waiting {wait_time}s for {description}...")
            await asyncio.sleep(wait_time)
            
            return ActionResult(
                extracted_content=f"Waited {wait_time} seconds for {description}",
                include_in_memory=True
            )
        
        @self.tools.action('Extract data from page (prices, names, emails, tables, lists)')
        async def extract_data(data_description: str, browser_session: BrowserSession) -> ActionResult:
            """
            Extract specific data from the current page.
            
            Args:
                data_description: What data to extract
            """
            self.logger.info(f"📊 Extracting: {data_description}")
            
            page = await browser_session.browser.get_current_page()
            
            # Get page text content
            try:
                content = await page.evaluate("() => document.body.innerText")
                return ActionResult(
                    extracted_content=f"Page content extracted. Contains {len(content)} characters.",
                    include_in_memory=True
                )
            except:
                return ActionResult(extracted_content="Page content extraction ready")
        
        @self.tools.action('Get personal information for form filling (name, email, phone, address)')
        async def get_personal_info(info_type: str, browser_session: BrowserSession) -> ActionResult:
            """
            Retrieve personal information from secure storage.
            
            Args:
                info_type: Type of info needed (name, email, phone, address, etc.)
            """
            self.logger.info(f"🔍 Getting personal info: {info_type}")
            
            info = self.store.get_personal_info(info_type)
            
            if not info:
                return ActionResult(
                    extracted_content=f"No stored {info_type}. Please add via setup.",
                    include_in_memory=True
                )
            
            return ActionResult(
                extracted_content=f"Retrieved {info_type}: {info}",
                include_in_memory=True
            )
    
    async def _auto_fill_login(self, page, credentials: Dict, llm) -> bool:
        """
        Auto-fill login forms using natural language element selection
        
        Args:
            page: Browser page object
            credentials: Dictionary with username and password
            llm: Language model for element selection
            
        Returns:
            True if successfully filled, False otherwise
        """
        try:
            await asyncio.sleep(1)
            
            # Find username/email field using natural language
            username_field = None
            try:
                username_field = await page.get_element_by_prompt(
                    "email or username input field to enter login credentials",
                    llm=llm
                )
            except Exception as e:
                self.logger.warning(f"Could not find username field: {e}")
            
            if not username_field:
                self.logger.warning("Username field not found")
                return False
            
            try:
                await username_field.click()
                await asyncio.sleep(0.3)
                await username_field.fill(credentials['username'])
                self.logger.info(f"✓ Filled username field")
                await asyncio.sleep(0.5)
            except Exception as e:
                self.logger.error(f"Error filling username: {e}")
                return False
            
            # Find password field using natural language
            password_field = None
            try:
                password_field = await page.get_element_by_prompt(
                    "password input field to enter the password",
                    llm=llm
                )
            except Exception as e:
                self.logger.warning(f"Could not find password field: {e}")
            
            if not password_field:
                self.logger.warning("Password field not found")
                return False
            
            try:
                await password_field.click()
                await asyncio.sleep(0.3)
                await password_field.fill(credentials['password'])
                self.logger.info(f"✓ Filled password field")
                await asyncio.sleep(0.5)
                return True
            except Exception as e:
                self.logger.error(f"Error filling password: {e}")
                return False
            
        except Exception as e:
            self.logger.error(f"Auto-fill error: {str(e)}", exc_info=True)
            return False
    
    def get_tools(self) -> Tools:
        """
        Return the complete tool suite
        
        Returns:
            Tools instance with all registered actions
        """
        return self.tools
