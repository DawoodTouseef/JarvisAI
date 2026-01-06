"""
DeepFinder - Your Smart AI Search Assistant
Discover and understand people better with comprehensive web intelligence
Scans and compiles publicly available information across the web and social media
"""

import os
import json
import warnings
from typing import Dict, List, Optional, Annotated
from datetime import datetime

# Suppress warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=RuntimeWarning)

# AutoGen imports
try:
    from autogen import ConversableAgent, register_function,GroupChat,GroupChatManager
    from autogen.agents.experimental.deep_research import DeepResearchAgent
    from autogen.agents.experimental.reasoning import ReasoningAgent
    from autogen.agents.experimental.websurfer import WebSurferAgent
    from autogen.agents.experimental.wikipedia import WikipediaAgent
except ImportError:
    import autogen
    from autogen import ConversableAgent, register_function

# Search engine imports

from playwright.sync_api import sync_playwright
from ddgs import DDGS
import requests
from bs4 import BeautifulSoup



class SearchEngineManager:
    """Manages multiple search engines for comprehensive information gathering"""
    
    def __init__(self):
        try:
            self.ddgs = DDGS()
        except:
            print("⚠️  Warning: DDGS initialization failed, will use fallback methods")
            self.ddgs = None
    
    def search_web(self, query: str, max_results: int = 8) -> List[Dict]:
        """Universal search method with automatic fallback"""
        
        # Try DuckDuckGo first (most reliable)
        results = self._search_duckduckgo(query, max_results)
        
        # If no results, try requests-based fallback
        if not results:
            results = self._search_with_requests(query, max_results)
        
        return results
    
    def _search_duckduckgo(self, query: str, max_results: int) -> List[Dict]:
        """Search using DuckDuckGo"""
        results = []
        try:
            if self.ddgs:
                ddgs_results = self.ddgs.text(query, max_results=max_results)
                for result in ddgs_results:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("href", ""),
                        "snippet": result.get("body", "")
                    })
        except Exception as e:
            pass
        
        return results
    
    def _search_with_requests(self, query: str, max_results: int) -> List[Dict]:
        """Fallback search using requests"""
        results = []
        try:
            url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            search_results = soup.find_all('div', class_='result')
            
            for result in search_results[:max_results]:
                try:
                    title_elem = result.find('a', class_='result__a')
                    snippet_elem = result.find('a', class_='result__snippet')
                    
                    if title_elem:
                        results.append({
                            "title": title_elem.get_text(strip=True),
                            "url": title_elem.get('href', ''),
                            "snippet": snippet_elem.get_text(strip=True) if snippet_elem else ""
                        })
                except:
                    continue
        except:
            pass
        
        return results
    
    def search_with_playwright(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search using Playwright browser automation (when enabled)"""
        results = []
        try:
            print(f"   🌐 Using Playwright to search: {query[:60]}...")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                page.goto(search_url, timeout=30000)
                page.wait_for_timeout(2000)
                
                search_results = page.query_selector_all("div.g")
                
                for result in search_results[:max_results]:
                    try:
                        title_elem = result.query_selector("h3")
                        link_elem = result.query_selector("a")
                        snippet_elem = result.query_selector("div.VwiC3b, div.IsZvec")
                        
                        if title_elem and link_elem:
                            title = title_elem.inner_text()
                            url = link_elem.get_attribute("href")
                            snippet = snippet_elem.inner_text() if snippet_elem else ""
                            
                            if title and url and not url.startswith('#'):
                                results.append({"title": title, "url": url, "snippet": snippet})
                    except:
                        continue
                
                browser.close()
        except Exception as e:
            results = self.search_web(query, max_results)
        
        return results


class DeepFinder:
    """
    DeepFinder - Your Smart AI Search Assistant
    Discover and understand people better with instant insights
    """
    
    def __init__(self):
        self.search_manager = SearchEngineManager()
        self.person_name = ""
        self.use_playwright = False
        self.setup_agents()
    
    def setup_agents(self):
        """Setup AutoGen AI agents for intelligent analysis"""
        
        llm_config = {
            "config_list": [{
                "model": "olmo2:latest",
                "api_type": "ollama",
            }],
        }
        
        # WebIntelligence Agent - Gathers comprehensive web intelligence
        self.web_intelligence_agent = DeepResearchAgent(
            name="WebIntelligenceAgent",
            system_message="""You are a Web Intelligence Specialist in DeepFinder. Your mission:
            
            1. Use web_search tool to discover information across multiple sources
            2. Search professional networks (LinkedIn, company websites)
            3. Search social media mentions (Twitter, Facebook, Instagram, YouTube)
            4. Search news articles, interviews, press releases
            5. Search academic profiles, publications, achievements
            
            Create strategic queries like:
            - "{person} professional profile career"
            - "{person} social media twitter instagram"
            - "{person} news interview article"
            - "{person} education background university"
            - "{person} achievements awards recognition"
            
            Cast a wide net to create a complete picture.""",
            llm_config=llm_config,
            human_input_mode="NEVER",
        )
        
        # ProfileAnalyzer Agent - Analyzes and structures the person's profile
        self.profile_analyzer = ConversableAgent(
            name="ProfileAnalyzer",
            system_message="""You are a Profile Analyzer in DeepFinder. Your role:
            
            Extract and organize information into a complete profile:
            
            📋 PROFESSIONAL PROFILE:
            - Current Position & Company
            - Career History
            - Industry & Expertise
            - Skills & Specializations
            
            🌐 DIGITAL PRESENCE:
            - LinkedIn, Twitter, Facebook, Instagram
            - Personal Website/Blog
            - GitHub, Portfolio
            - YouTube Channel
            
            🎓 BACKGROUND:
            - Education (Universities, Degrees)
            - Certifications
            - Publications & Research
            
            ⭐ ACHIEVEMENTS & RECOGNITION:
            - Awards & Honors
            - Notable Projects
            - Media Mentions
            - Speaking Engagements
            
            📍 LOCATION & NETWORK:
            - Current Location
            - Past Locations
            - Professional Connections
            
            Be comprehensive but concise. Focus on verified, public information.""",
            llm_config=llm_config,
            human_input_mode="NEVER",
        )
        
        # VerificationSpecialist Agent - Ensures accuracy
        self.verification_specialist = WebSurferAgent(
            name="VerificationSpecialist",
            system_message="""You are a Verification Specialist in DeepFinder. Your critical role:
            
            1. Cross-verify information from multiple sources
            2. Flag inconsistencies or contradictions
            3. Rate confidence level for each data point
            4. Use web_search to fact-check suspicious claims
            5. Use human_input_tool when clarification is needed
            6. Distinguish between verified facts and unverified claims
            
            Verification Criteria:
            ✓ VERIFIED: Multiple reliable sources confirm
            ~ LIKELY: One reliable source, seems credible
            ? UNVERIFIED: Single source, needs confirmation
            ✗ CONFLICTING: Multiple sources disagree
            
            Be thorough and maintain high accuracy standards.""",
            llm_config=llm_config,
            human_input_mode="NEVER",
            web_tool="browser_use",
        )
        
        # InsightGenerator Agent - Creates the final comprehensive report
        self.insight_generator = ConversableAgent(
            name="InsightGenerator",
            system_message="""You are an Insight Generator in DeepFinder. Your mission:
            
            Create a compelling, comprehensive profile report that includes:
            
            1. EXECUTIVE SUMMARY - Who is this person in 2-3 sentences
            2. PROFESSIONAL IDENTITY - Career, expertise, current role
            3. DIGITAL FOOTPRINT - Online presence and social activity
            4. NOTABLE ACHIEVEMENTS - What they're known for
            5. BACKGROUND - Education, origins, journey
            6. PUBLIC PERCEPTION - How they're seen/mentioned online
            7. KEY INSIGHTS - Interesting facts, patterns, highlights
            8. VERIFICATION STATUS - What's confirmed vs uncertain
            
            Make it:
            - Easy to read and scan
            - Factual and professional
            - Comprehensive yet concise
            - Actionable and insightful
            
            This report helps users understand people better instantly.""",
            llm_config=llm_config,
            human_input_mode="NEVER",
        )
        
        # UserProxy - Manages workflow
        self.user_proxy = ReasoningAgent(
            name="Coordinator",
            system_message="You coordinate the DeepFinder workflow and execute tools.",
            llm_config=False,
            human_input_mode="NEVER",
        )
        self.group_chat = GroupChat(agents=[
            self.web_intelligence_agent,
                                          self.profile_analyzer,
                                          self.verification_specialist,
                                          self.insight_generator,
                                          self.user_proxy,
                                          WikipediaAgent(name="WikipediaAgent", llm_config=llm_config)],
                                    speaker_selection_method="auto",
                                    select_speaker_auto_llm_config=llm_config,
                                    select_speaker_auto_verbose=True
                                    )
        self.group_chat_manager = GroupChatManager(groupchat=self.group_chat)
    
    def web_search_tool(self, query: Annotated[str, "Search query to find information"]) -> str:
        """Tool for agents to search the web"""
        
        print(f"   🔍 Searching: {query[:60]}...")
        
        if self.use_playwright:
            results = self.search_manager.search_with_playwright(query, max_results=8)
        else:
            results = self.search_manager.search_web(query, max_results=8)
        
        if not results:
            return "⚠️ No results found for this query. Try a different search."
        
        print(f"   ✓ Found {len(results)} results")
        
        # Format results
        formatted = []
        for i, r in enumerate(results[:8], 1):
            formatted.append(
                f"{i}. {r.get('title', 'N/A')}\n"
                f"   URL: {r.get('url', 'N/A')}\n"
                f"   Info: {r.get('snippet', 'N/A')[:250]}...\n"
            )
        
        return "\n".join(formatted)
    
    def human_input_tool(self, question: Annotated[str, "Question for the user"]) -> str:
        """Tool for agents to ask user questions"""
        
        print(f"\n{'='*70}")
        print("💬 DEEPFINDER NEEDS YOUR INPUT")
        print(f"{'='*70}")
        print(f"\n{question}\n")
        
        response = input("👤 Your Answer: ").strip()
        
        if not response:
            response = "No answer provided"
        
        print(f"\n✓ Recorded: {response}\n")
        print(f"{'='*70}\n")
        
        return response
    
    def register_tools(self):
        """Register tools with agents"""
        
        def web_search(query: Annotated[str, "Search query to find information"]) -> str:
            return self.web_search_tool(query)
        
        def human_input(question: Annotated[str, "Question for the user"]) -> str:
            return self.human_input_tool(question)
        # Register web_search for all intelligence agents
        for agent in [self.web_intelligence_agent, self.verification_specialist]:
            register_function(
                web_search,
                caller=agent,
                executor=self.user_proxy,
                name="web_search",
                description="Search the web for information about people."
            )
        
        # Register human_input for verification
        register_function(
            human_input,
            caller=self.verification_specialist,
            executor=self.user_proxy,
            name="human_input_tool",
            description="Ask the user a question when you need clarification."
        )
    
    def discover_person(self, name: str, enable_playwright: bool = False) -> Dict:
        """
        Main method: Discover and understand a person
        
        Args:
            name: Full name of the person to research
            enable_playwright: Use browser automation for more results
            
        Returns:
            Comprehensive profile report
        """
        
        self.person_name = name
        self.use_playwright = enable_playwright
        
        print(f"\n{'='*70}")
        print(f"🔍 DEEPFINDER - Smart AI Search Assistant")
        print(f"{'='*70}")
        print(f"📝 Researching: {name}")
        print(f"🌐 Method: {'Browser Automation' if enable_playwright else 'Web Search'}")
        print(f"🤖 AI Agents: Intelligence → Analysis → Verification → Insights")
        print(f"{'='*70}\n")
        
        # Register tools
        self.register_tools()
        
        # Run intelligent discovery workflow
        print("🚀 Starting AI-Powered Discovery...\n")
        report = self.run_discovery_workflow(name)
        
        return report
    
    def run_discovery_workflow(self, name: str) -> Dict:
        """Run the complete AI discovery workflow"""
        
        try:
            # Phase 1: Web Intelligence Gathering
            print("🌐 Phase 1: Scanning web and social media...")
            intelligence_prompt = f"""
DeepFinder Mission: Create a complete picture of {name}

Use web_search tool to discover:

1. Professional Profile:
   - Search: "{name} LinkedIn profile career"
   - Search: "{name} company job position"

2. Social Media Presence:
   - Search: "{name} Twitter social media"
   - Search: "{name} Instagram Facebook profile"

3. Public Mentions:
   - Search: "{name} news article interview"
   - Search: "{name} press release announcement"

4. Achievements:
   - Search: "{name} awards achievements recognition"
   - Search: "{name} publications projects"

5. Background:
   - Search: "{name} education university background"
   - Search: "{name} biography about"

Gather comprehensive intelligence from all angles.
"""
            
            intelligence_chat = self.group_chat_manager.initiate_chat(
                self.web_intelligence_agent,
                message=intelligence_prompt,
                max_turns=10,
                )
            
            intelligence_data = self._extract_chat_content(intelligence_chat)
            
            # Phase 2: Profile Analysis
            print("\n📊 Phase 2: Analyzing and organizing profile...")
            analysis_prompt = f"""
Analyze all discovered information about {name}:

{intelligence_data}

Create a structured profile with:
- Professional Identity (current role, career, expertise)
- Digital Presence (all social media, websites)
- Education & Background
- Achievements & Recognition
- Location & Network
- Key Facts

Organize everything clearly and comprehensively.
"""
            
            analysis_chat = self.user_proxy.initiate_chat(
                self.profile_analyzer,
                message=analysis_prompt,
                max_turns=3,
            )
            
            analyzed_profile = self._extract_chat_content(analysis_chat)
            
            # Phase 3: Verification
            print("\n✅ Phase 3: Verifying accuracy and reliability...")
            verification_prompt = f"""
Verify the profile of {name}:

{analyzed_profile}

Tasks:
1. Cross-check facts from multiple sources
2. Use web_search to verify suspicious information
3. Flag inconsistencies or conflicts
4. Rate confidence for each section (VERIFIED/LIKELY/UNVERIFIED)
5. Use human_input_tool if you need clarification
6. Mark what's confirmed vs uncertain

Maintain high accuracy standards.
"""
            
            verification_chat = self.user_proxy.initiate_chat(
                self.verification_specialist,
                message=verification_prompt,
                max_turns=8,
            )
            
            verified_profile = self._extract_chat_content(verification_chat)
            
            # Phase 4: Generate Insights
            print("\n💡 Phase 4: Generating comprehensive insights...")
            insights_prompt = f"""
Create DeepFinder's comprehensive profile report for {name}:

Verified Profile:
{verified_profile}

Generate a report with:

1. EXECUTIVE SUMMARY (2-3 sentences: Who are they?)
2. PROFESSIONAL IDENTITY (Career, role, expertise)
3. DIGITAL FOOTPRINT (Social media, online presence)
4. ACHIEVEMENTS & RECOGNITION (What they're known for)
5. BACKGROUND & EDUCATION
6. PUBLIC PERCEPTION (How they're mentioned online)
7. KEY INSIGHTS (Interesting facts, patterns)
8. VERIFICATION STATUS (What's confirmed)
9. INFORMATION SOURCES (Key URLs)

Make it comprehensive, professional, and easy to understand.
This helps users "discover and understand people better."
"""
            
            insights_chat = self.user_proxy.initiate_chat(
                self.insight_generator,
                message=insights_prompt,
                max_turns=3,
            )
            
            final_insights = self._extract_chat_content(insights_chat)
            
            # Create structured report
            report = {
                "person": name,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "deepfinder_version": "4.0",
                "status": "✅ Profile Discovered & Verified",
                "ai_agents_used": [
                    "WebIntelligenceAgent",
                    "ProfileAnalyzer", 
                    "VerificationSpecialist",
                    "InsightGenerator"
                ],
                "intelligence_data": intelligence_data[:1000] + "...",
                "analyzed_profile": analyzed_profile[:1000] + "...",
                "verified_profile": verified_profile[:1000] + "...",
                "comprehensive_insights": final_insights,
                "tagline": "DeepFinder: Discover and understand people better, anytime, anywhere."
            }
            
            print("\n✅ Discovery Complete! Profile Ready.\n")
            
        except Exception as e:
            print(f"\n❌ Error during discovery: {e}")
            report = {
                "person": name,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "❌ Error",
                "error": str(e),
                "note": "Please check your Ollama setup and try again."
            }
        
        return report
    
    def _extract_chat_content(self, chat_result) -> str:
        """Extract content from agent chat"""
        content = []
        
        try:
            if hasattr(chat_result, 'chat_history'):
                for msg in chat_result.chat_history:
                    if isinstance(msg, dict) and msg.get('content'):
                        content.append(msg['content'])
        except:
            pass
        
        return "\n\n".join(content) if content else "No content"
    
    def print_report(self, report: Dict):
        """Print beautiful formatted report"""
        
        print(f"\n{'='*70}")
        print(f"📋 DEEPFINDER PROFILE REPORT")
        print(f"{'='*70}\n")
        
        print(f"👤 Person: {report.get('person', 'N/A')}")
        print(f"📅 Generated: {report.get('generated_at', 'N/A')}")
        print(f"🎯 Status: {report.get('status', 'N/A')}\n")
        
        if 'ai_agents_used' in report:
            print(f"🤖 AI Agents: {', '.join(report['ai_agents_used'])}\n")
        
        print(f"{'─'*70}\n")
        
        if 'comprehensive_insights' in report:
            print(report['comprehensive_insights'])
        elif 'error' in report:
            print(f"❌ Error: {report['error']}")
            print(f"\n💡 {report.get('note', '')}")
        
        print(f"\n{'─'*70}")
        print(f"✨ {report.get('tagline', 'DeepFinder: Your Smart AI Search Assistant')}")
        print(f"{'─'*70}\n")


def main():
    """Main function"""
    
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║                    🔍 DEEPFINDER v4.0                          ║
║                                                                ║
║            Your Smart AI Search Assistant                      ║
║                                                                ║
║   Discover and understand people better with just a name.     ║
║   Scans and compiles publicly available information across    ║
║   the web and social media, creating a complete picture.      ║
║                                                                ║
║   📊 Professional Backgrounds  |  🌐 Social Media Presence    ║
║   🎓 Education & Achievements  |  ⭐ Public Recognition       ║
║   💼 Career History            |  📍 Location & Network        ║
║                                                                ║
║              Get instant insights, anytime, anywhere.          ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    print("\n⚙️  Requirements:")
    print("   ✓ Ollama running (http://localhost:11434)")
    print("   ✓ Internet connection\n")
    
    print("🤖 AI-Powered Features:")
    print("   • Multi-agent intelligence gathering")
    print("   • Cross-platform social media scanning")
    print("   • Automated verification & fact-checking")
    print("   • Comprehensive profile generation")
    print("   • Human-in-the-loop for accuracy\n")
    
    deepfinder = DeepFinder()
    
    # Get person name
    person_name = input("👤 Enter person's full name: ").strip()
    
    if not person_name:
        print("❌ Please enter a valid name!")
        return
    
    # Optional: Enable browser automation
    use_browser = input("\n🌐 Use browser automation for more results? (y/N): ").strip().lower()
    enable_playwright = use_browser == 'y'
    
    if enable_playwright:
        print("⚙️  Browser automation enabled (slower but more comprehensive)")
    
    print("\n💡 Tip: DeepFinder AI may ask questions to verify information!\n")
    
    # Discover person
    try:
        report = deepfinder.discover_person(person_name, enable_playwright)
        
        # Print report
        deepfinder.print_report(report)
        
        # Save option
        if report.get('status', '').startswith('✅'):
            save = input("\n💾 Save profile report to JSON? (y/n): ").strip().lower()
            if save == 'y':
                filename = f"deepfinder_{person_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                print(f"✅ Saved: {filename}")
        
        print("\n🎉 Thank you for using DeepFinder!")
        print("💡 Discover and understand people better, anytime, anywhere.\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user.")
    


if __name__ == "__main__":
    main()