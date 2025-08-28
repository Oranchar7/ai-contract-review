#!/usr/bin/env python3
"""
Test RAG System - Verify trained documents can be retrieved and used for contract analysis
"""

import asyncio
import sys
from services.pinecone_rag_service import PineconeRAGService

async def test_rag_system():
    """Test the RAG system with various contract-related queries"""
    rag_service = PineconeRAGService()
    
    print("🧪 Testing RAG System with Trained Legal Documents")
    print("=" * 55)
    
    # Check if service is available
    if not rag_service.is_available():
        print("❌ RAG service not available")
        return
    
    # Get index stats
    if rag_service.index:
        stats = rag_service.index.describe_index_stats()
        print(f"📊 Pinecone index vectors: {stats.total_vector_count}")
    
    # Test queries
    test_queries = [
        {
            "query": "What are the key provisions in an NDA?",
            "expected_topics": ["confidential information", "non-disclosure", "obligations"]
        },
        {
            "query": "What payment terms are typically included in service agreements?", 
            "expected_topics": ["30 days", "payment", "invoices"]
        },
        {
            "query": "What is a force majeure clause?",
            "expected_topics": ["circumstances beyond control", "natural disasters", "delays"]
        },
        {
            "query": "What are typical SLA metrics for uptime?",
            "expected_topics": ["99.9%", "uptime", "availability", "downtime"]
        },
        {
            "query": "What intellectual property provisions are common in employment agreements?",
            "expected_topics": ["work product", "inventions", "Company owns", "assigns rights"]
        }
    ]
    
    print(f"\n🔍 Running {len(test_queries)} test queries...")
    print("-" * 55)
    
    successful_tests = 0
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: {test['query']}")
        
        try:
            # Query the RAG system
            result = await rag_service.ask_contract(
                query=test['query'],
                jurisdiction="US-Federal",
                contract_type="General"
            )
            
            # Check for errors first
            if result.get("error"):
                print(f"❌ Query failed: {result.get('error')}")
                if result.get("details"):
                    print(f"   Details: {result.get('details')}")
                continue
            
            # Look for response in different possible fields
            response = result.get("response") or result.get("summary") or ""
            
            if response and len(response.strip()) > 20:
                chunks_used = result.get("retrieved_chunks", 0) 
                confidence = result.get("confidence_score", result.get("overall_risk_score", 0))
                
                print(f"✅ Response received ({chunks_used} chunks, confidence: {confidence:.2f})")
                print(f"📄 Response preview: {response[:200]}...")
                
                # Check if expected topics are mentioned
                response_lower = response.lower()
                topics_found = [topic for topic in test['expected_topics'] 
                              if any(word in response_lower for word in topic.lower().split())]
                
                if topics_found:
                    print(f"🎯 Found expected topics: {', '.join(topics_found)}")
                    successful_tests += 1
                else:
                    print(f"⚠️  Expected topics not found: {test['expected_topics']}")
                
            else:
                print(f"❌ No meaningful response received")
                print(f"   Available keys: {list(result.keys())}")
                if len(str(result)) < 300:
                    print(f"   Full result: {result}")
                
        except Exception as e:
            print(f"❌ Query failed: {str(e)}")
    
    # Summary
    print(f"\n📊 RAG Test Results:")
    print(f"   Successful queries: {successful_tests}/{len(test_queries)}")
    print(f"   Success rate: {(successful_tests/len(test_queries))*100:.1f}%")
    
    if successful_tests >= len(test_queries) * 0.8:  # 80% success rate
        print(f"🎉 RAG system is working well with trained documents!")
        return True
    else:
        print(f"⚠️  RAG system needs improvement or more training data")
        return False

async def test_telegram_integration():
    """Test RAG integration with Telegram bot queries"""
    print(f"\n🤖 Testing Telegram Bot Integration")
    print("-" * 40)
    
    # Import telegram processing function
    try:
        from main import process_telegram_query
        
        test_messages = [
            "What should I look for in an NDA?",
            "Tell me about service level agreements",
            "What are typical payment terms?"
        ]
        
        for query in test_messages:
            print(f"\n💬 Testing: \"{query}\"")
            
            message_data = {
                'chat_id': 999999,
                'user_id': 999999,
                'text': query,
                'first_name': 'TestUser'
            }
            
            try:
                response = await process_telegram_query(query, message_data)
                if response and len(response.strip()) > 50:  # Substantial response
                    print(f"✅ Bot responded ({len(response)} chars)")
                    print(f"📄 Preview: {response[:150]}...")
                else:
                    print(f"⚠️  Short or empty response: {response}")
                    
            except Exception as e:
                print(f"❌ Bot query failed: {str(e)}")
                
    except ImportError as e:
        print(f"❌ Cannot test Telegram integration: {str(e)}")

async def main():
    """Main test function"""
    print("🚀 RAG System Verification Suite")
    print("=" * 40)
    
    # Test RAG system directly
    rag_success = await test_rag_system()
    
    # Test Telegram integration if RAG works
    if rag_success:
        await test_telegram_integration()
    
    print(f"\n✨ RAG Training and Testing Complete!")

if __name__ == "__main__":
    asyncio.run(main())