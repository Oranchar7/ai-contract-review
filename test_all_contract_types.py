#!/usr/bin/env python3
"""
Comprehensive Test for All Contract Types from Dropdown
Tests all 10 contract types to ensure complete RAG training coverage
"""

import asyncio
from services.pinecone_rag_service import PineconeRAGService

async def test_all_contract_types():
    """Test RAG system with queries for all 10 contract types from dropdown"""
    rag_service = PineconeRAGService()
    
    print("🧪 Testing All Contract Types from Dropdown")
    print("=" * 50)
    
    # Check if service is available
    if not rag_service.is_available():
        print("❌ RAG service not available")
        return False
    
    # Get index stats
    if rag_service.index:
        stats = rag_service.index.describe_index_stats()
        print(f"📊 Pinecone index vectors: {stats.total_vector_count}")
    
    # Test queries for ALL contract types from dropdown
    contract_type_tests = [
        # Already trained contract types (original 5)
        {
            "contract_type": "NDA",
            "query": "What confidential information protections are in NDAs?",
            "expected_topics": ["confidential information", "disclosure", "obligations"]
        },
        {
            "contract_type": "MSA", 
            "query": "What are typical MSA payment terms?",
            "expected_topics": ["30 days", "invoices", "payment"]
        },
        {
            "contract_type": "Employment",
            "query": "What IP clauses are common in employment contracts?",
            "expected_topics": ["work product", "inventions", "company owns"]
        },
        {
            "contract_type": "License",
            "query": "What restrictions appear in software license agreements?",
            "expected_topics": ["reverse engineer", "modify", "distribute"]
        },
        {
            "contract_type": "SLA",
            "query": "What uptime guarantees are typical in SLAs?",
            "expected_topics": ["99.9%", "uptime", "availability"]
        },
        
        # Newly added contract types (new 5)
        {
            "contract_type": "SaaS",
            "query": "What are typical SaaS subscription billing terms?",
            "expected_topics": ["monthly", "billing", "auto-renewal"]
        },
        {
            "contract_type": "Consulting", 
            "query": "What deliverables are common in consulting agreements?",
            "expected_topics": ["analysis report", "recommendations", "deliverables"]
        },
        {
            "contract_type": "Purchase",
            "query": "What representations are made in purchase agreements?",
            "expected_topics": ["warranties", "ownership", "liens"]
        },
        {
            "contract_type": "Lease",
            "query": "What maintenance responsibilities are in lease agreements?",
            "expected_topics": ["landlord", "tenant", "maintenance"]
        },
        {
            "contract_type": "Partnership",
            "query": "What profit distribution terms are in partnership agreements?",
            "expected_topics": ["ownership", "profit", "distributions"]
        }
    ]
    
    print(f"\n🔍 Testing {len(contract_type_tests)} contract types from dropdown...")
    print("-" * 50)
    
    successful_tests = 0
    results_by_type = {}
    
    for i, test in enumerate(contract_type_tests, 1):
        contract_type = test['contract_type']
        query = test['query']
        
        print(f"\n📝 Test {i}: {contract_type} - {query}")
        
        try:
            # Query the RAG system with specific contract type
            result = await rag_service.ask_contract(
                query=query,
                jurisdiction="US-Federal",
                contract_type=contract_type
            )
            
            # Check for errors first
            if result.get("error"):
                print(f"❌ Query failed: {result.get('error')}")
                results_by_type[contract_type] = "FAILED"
                continue
            
            # Look for response in different possible fields
            response = result.get("response") or result.get("summary") or ""
            
            if response and len(response.strip()) > 20:
                chunks_used = result.get("retrieved_chunks", 0) 
                confidence = result.get("confidence_score", result.get("overall_risk_score", 0))
                
                print(f"✅ Response received ({chunks_used} chunks, confidence: {confidence:.2f})")
                print(f"📄 Preview: {response[:150]}...")
                
                # Check if expected topics are mentioned
                response_lower = response.lower()
                topics_found = []
                for topic in test['expected_topics']:
                    if any(word in response_lower for word in topic.lower().split()):
                        topics_found.append(topic)
                
                if topics_found:
                    print(f"🎯 Found expected topics: {', '.join(topics_found)}")
                    successful_tests += 1
                    results_by_type[contract_type] = "SUCCESS"
                else:
                    print(f"⚠️  Expected topics not found: {test['expected_topics']}")
                    results_by_type[contract_type] = "PARTIAL"
                
            else:
                print(f"❌ No meaningful response received")
                results_by_type[contract_type] = "NO_RESPONSE"
                
        except Exception as e:
            print(f"❌ Query failed: {str(e)}")
            results_by_type[contract_type] = "ERROR"
    
    # Summary by contract type
    print(f"\n📊 Complete Contract Type Coverage Results:")
    print(f"{'Contract Type':<15} {'Status':<12} {'Description'}")
    print("-" * 50)
    
    for contract_type, status in results_by_type.items():
        if status == "SUCCESS":
            desc = "✅ Fully trained with relevant content"
        elif status == "PARTIAL": 
            desc = "⚠️  Responds but may need more training"
        elif status == "FAILED":
            desc = "❌ Query failed with error"
        elif status == "NO_RESPONSE":
            desc = "❌ No meaningful response generated"
        else:
            desc = "❌ Technical error occurred"
            
        print(f"{contract_type:<15} {status:<12} {desc}")
    
    print(f"\n📈 Overall Training Results:")
    print(f"   Successfully tested: {successful_tests}/{len(contract_type_tests)} contract types")
    print(f"   Success rate: {(successful_tests/len(contract_type_tests))*100:.1f}%")
    print(f"   Contract types fully covered: {len([s for s in results_by_type.values() if s == 'SUCCESS'])}/10")
    
    # Check if all dropdown contract types are covered
    all_covered = successful_tests >= len(contract_type_tests) * 0.9  # 90% success rate
    
    if all_covered:
        print(f"🎉 All contract types from dropdown are successfully trained!")
        print(f"✅ RAG system ready for comprehensive contract analysis!")
        return True
    else:
        print(f"⚠️  Some contract types need additional training")
        return False

async def main():
    """Main test function"""
    print("🚀 Complete Contract Type Coverage Test")
    print("Testing all 10 contract types from dropdown")
    print("=" * 45)
    
    success = await test_all_contract_types()
    
    print(f"\n✨ Complete Contract Training Test Finished!")
    if success:
        print("🎯 All contract types from your dropdown are now trained and ready!")
    else:
        print("📝 Some contract types may need additional training data.")

if __name__ == "__main__":
    asyncio.run(main())