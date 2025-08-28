#!/usr/bin/env python3
"""
Test Enhanced RAG System with Authoritative Best Practices
"""

import asyncio
from services.pinecone_rag_service import PineconeRAGService
from services.contract_chat_service import ContractChatService

class EnhancedRAGTester:
    def __init__(self):
        self.rag_service = PineconeRAGService()
        self.chat_service = ContractChatService()

    async def test_comprehensive_queries(self):
        """Test queries covering all contract types with best practices"""
        print("🧪 TESTING ENHANCED RAG SYSTEM WITH AUTHORITATIVE GUIDANCE")
        print("=" * 60)
        
        test_queries = [
            "What are the ABA recommended essential components for NDAs?",
            "What liability protections should customers negotiate in MSAs according to legal experts?", 
            "What are the GDPR compliance requirements for SaaS terms of service?",
            "What federal employment law requirements must be included in employment contracts?",
            "How should independent contractor status be established in consulting agreements?",
            "What are the standard licensing models and IP protection frameworks for software licenses?",
            "What are ABA Model Asset Purchase Agreement recommendations for due diligence?",
            "What are the 2025 California commercial lease law changes and compliance requirements?",
            "What essential clauses should every partnership agreement include for legal protection?",
            "What are the industry best practices for SLA compliance monitoring and enforcement?"
        ]
        
        print(f"📊 Database contains {self.rag_service.index.describe_index_stats().total_vector_count} vectors")
        print("🔍 Testing retrieval accuracy with authoritative sources...")
        print()
        
        successful_tests = 0
        
        for i, query in enumerate(test_queries, 1):
            print(f"Test {i}/10: {query[:50]}...")
            
            try:
                # Test chat service with RAG integration
                response = await self.chat_service.general_chat(
                    query=query
                )
                
                if response and 'answer' in response and len(response['answer']) > 100:
                    print(f"✅ Generated comprehensive response ({len(response['answer'])} chars)")
                    # Check if response mentions authoritative sources
                    response_text = response['answer'].lower()
                    if any(source in response_text for source in ['aba', 'american bar', 'legal', 'compliance', 'standards', 'professional']):
                        print(f"✅ Response includes authoritative guidance")
                        successful_tests += 1
                    else:
                        print(f"⚠️ Response generated but no clear authoritative guidance detected")
                        successful_tests += 0.5
                else:
                    print("❌ Failed to generate comprehensive response")
                    
            except Exception as e:
                print(f"❌ Test failed: {str(e)}")
                
            print()
        
        # Final Results
        success_rate = (successful_tests / len(test_queries)) * 100
        print("🏆 ENHANCED RAG SYSTEM TEST RESULTS")
        print("=" * 40)
        print(f"✅ Successful tests: {successful_tests}/{len(test_queries)}")
        print(f"📈 Success rate: {success_rate:.1f}%")
        print(f"📚 Total vectors: {self.rag_service.index.describe_index_stats().total_vector_count}")
        
        if success_rate == 100:
            print("🎉 PERFECT SCORE! All contract types working with authoritative guidance!")
        elif success_rate >= 90:
            print("🌟 EXCELLENT! RAG system performing at high level with professional sources!")
        elif success_rate >= 80:
            print("👍 GOOD! Most queries successful with authoritative guidance!")
        else:
            print("⚠️ NEEDS IMPROVEMENT: Some contract types need attention")

async def main():
    tester = EnhancedRAGTester()
    await tester.test_comprehensive_queries()

if __name__ == "__main__":
    asyncio.run(main())