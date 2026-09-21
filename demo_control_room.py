#!/usr/bin/env python3
"""
Demo script to show the Control Room in action!

This script:
1. Triggers multiple PR review agents in parallel
2. Shows how they appear in the control room dashboard
3. Demonstrates real-time updates
"""

import asyncio
import httpx
import sys


async def trigger_review(repo_path: str, branch: str, agent_num: int):
    """Trigger a PR review agent."""
    print(f"🚀 Starting Agent #{agent_num} for {repo_path}...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                "http://localhost:8888/agent/review",
                json={
                    "repo_path": repo_path,
                    "target_branch": "main",
                    "current_branch": branch
                }
            )
            
            result = response.json()
            print(f"✅ Agent #{agent_num} completed!")
            print(f"   Steps taken: {result['steps_taken']}")
            print(f"   Success: {result['success']}")
            
            return result
            
        except Exception as e:
            print(f"❌ Agent #{agent_num} failed: {e}")
            return None


async def main():
    """Run the demo."""
    print("""
╔══════════════════════════════════════════════════════════╗
║  🎮 Agentic SDLC Platform - Control Room Demo          ║
╚══════════════════════════════════════════════════════════╝

This demo will:
1. Launch multiple agents in parallel
2. Each agent will review different repos
3. Open http://localhost:8888 in your browser to watch!

Press Enter when you have the dashboard open...
""")
    
    input()
    
    print("\n🎬 Starting demo in 3 seconds...")
    await asyncio.sleep(1)
    print("🎬 Starting demo in 2 seconds...")
    await asyncio.sleep(1)
    print("🎬 Starting demo in 1 second...")
    await asyncio.sleep(1)
    print("\n🚀 LAUNCHING AGENTS!\n")
    
    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            health = await client.get("http://localhost:8888/health")
            if health.status_code != 200:
                print("❌ Server is not running! Start it with: python3 main.py")
                return
    except Exception:
        print("❌ Server is not running! Start it with: python3 main.py")
        return
    
    # Trigger multiple agents
    # (Use different repos if you have them, or same repo with different branches)
    tasks = [
        trigger_review("/Users/ajain/pcp-repos/agentic-system", "main", 1),
        # Add more repos here if you want to see multiple agents!
        # trigger_review("/path/to/repo2", "feature-branch", 2),
        # trigger_review("/path/to/repo3", "develop", 3),
    ]
    
    # Run all agents concurrently!
    results = await asyncio.gather(*tasks)
    
    print("\n" + "="*60)
    print("📊 Demo Complete!")
    print("="*60)
    
    successful = sum(1 for r in results if r and r['success'])
    print(f"✅ Successful reviews: {successful}/{len(results)}")
    
    print("\n💡 What you should have seen in the dashboard:")
    print("   1. Agent cards appearing with thinking status")
    print("   2. Flow boxes (Think → Act → Observe) animating")
    print("   3. Live trace showing each step")
    print("   4. Cards completing with ✅ or ❌")
    print("   5. Metrics updating in real-time")
    
    print("\n🎓 Try This Next:")
    print("   - Add more repos to the tasks list above")
    print("   - Create different agent types (Fixer, Tester, etc.)")
    print("   - Build agent-to-agent communication")
    print("   - Add your own tools!")
    
    print("\n📖 Read CONTROL_ROOM.md for the complete guide!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted. Goodbye!")
        sys.exit(0)
