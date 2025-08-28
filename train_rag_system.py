#!/usr/bin/env python3
"""
RAG Training Script for AI Contract Review System
Uploads sample legal documents to train the RAG agent with contract knowledge
"""

import asyncio
import os
from services.pinecone_rag_service import PineconeRAGService

class RAGTrainer:
    def __init__(self):
        self.rag_service = PineconeRAGService()
        
    async def upload_training_document(self, text: str, filename: str, jurisdiction: str = "US-Federal", contract_type: str = "General"):
        """Upload a single training document to the RAG system"""
        print(f"🔄 Uploading: {filename}")
        
        result = await self.rag_service.upload_contract(
            contract_text=text,
            filename=filename,
            email="training@system.local",
            jurisdiction=jurisdiction,
            contract_type=contract_type
        )
        
        if result.get("status") == "success":
            chunks_created = result.get("chunks_created", 0)
            chunks_skipped = result.get("chunks_skipped", 0)
            total_tokens = result.get("total_tokens", 0)
            
            print(f"✅ {filename}: {chunks_created} chunks created, {chunks_skipped} skipped ({total_tokens} tokens)")
        else:
            print(f"❌ {filename}: {result.get('error', 'Unknown error')}")
        
        return result
    
    async def get_index_stats(self):
        """Get current Pinecone index statistics"""
        if self.rag_service.index:
            stats = self.rag_service.index.describe_index_stats()
            return stats.total_vector_count
        return 0
    
    async def train_with_sample_documents(self):
        """Train RAG system with comprehensive legal document samples"""
        print("🚀 Starting RAG Training Process...")
        
        # Check initial state
        initial_vectors = await self.get_index_stats()
        print(f"📊 Initial vectors in database: {initial_vectors}")
        
        # Sample legal documents for training
        training_documents = [
            {
                "filename": "sample_nda.txt",
                "contract_type": "NDA",
                "jurisdiction": "US-Federal",
                "text": self.get_nda_sample()
            },
            {
                "filename": "sample_msa.txt", 
                "contract_type": "MSA",
                "jurisdiction": "US-Federal",
                "text": self.get_msa_sample()
            },
            {
                "filename": "sample_sla.txt",
                "contract_type": "SLA", 
                "jurisdiction": "US-Federal",
                "text": self.get_sla_sample()
            },
            {
                "filename": "employment_agreement.txt",
                "contract_type": "Employment",
                "jurisdiction": "US-NY", 
                "text": self.get_employment_sample()
            },
            {
                "filename": "software_license.txt",
                "contract_type": "License",
                "jurisdiction": "US-CA",
                "text": self.get_software_license_sample()
            }
        ]
        
        # Upload all training documents
        results = []
        for doc in training_documents:
            result = await self.upload_training_document(
                text=doc["text"],
                filename=doc["filename"], 
                jurisdiction=doc["jurisdiction"],
                contract_type=doc["contract_type"]
            )
            results.append(result)
            
            # Small delay to avoid rate limits
            await asyncio.sleep(1)
        
        # Check final state
        final_vectors = await self.get_index_stats()
        print(f"\n📈 Training Complete!")
        print(f"📊 Final vectors in database: {final_vectors}")
        print(f"🆕 New vectors added: {final_vectors - initial_vectors}")
        
        return results
    
    def get_nda_sample(self):
        return """NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is made between TechCorp Inc. ("Disclosing Party") and ClientCo LLC ("Receiving Party").

1. DEFINITION OF CONFIDENTIAL INFORMATION
"Confidential Information" means any technical data, trade secrets, know-how, research, product plans, products, services, customers, customer lists, markets, software, developments, inventions, processes, formulas, technology, designs, drawings, engineering, hardware configuration information, marketing, finances, or other business information.

2. OBLIGATIONS OF RECEIVING PARTY
The Receiving Party agrees to:
- Hold all Confidential Information in strict confidence
- Not disclose Confidential Information to third parties without written consent
- Use Confidential Information solely for evaluation purposes
- Return all Confidential Information upon request

3. EXCEPTIONS
This Agreement does not apply to information that:
- Is publicly known through no breach of this Agreement
- Is rightfully received from a third party
- Was known prior to disclosure
- Is independently developed

4. TERM AND TERMINATION
This Agreement shall remain in effect for 5 years from the date of execution. Obligations shall survive termination.

5. REMEDIES
The parties acknowledge that any breach may cause irreparable harm and agree that equitable relief may be sought.

6. GOVERNING LAW
This Agreement shall be governed by federal laws and the laws of the State of Delaware."""

    def get_msa_sample(self):
        return """MASTER SERVICE AGREEMENT

This Master Service Agreement ("MSA") is entered into between ServiceProvider Inc. ("Provider") and Enterprise Client Corp. ("Client").

1. SCOPE OF SERVICES
Provider shall provide professional services as detailed in separate Statements of Work ("SOWs") executed under this MSA.

2. PAYMENT TERMS
- Invoices payable within 30 days of receipt
- Late payments subject to 1.5% monthly interest charge
- Client responsible for reasonable collection costs
- Time and materials billed at agreed hourly rates

3. INTELLECTUAL PROPERTY
- Provider retains rights to pre-existing IP and general methodologies
- Client owns work product specifically created for Client
- Provider grants Client non-exclusive license to use deliverables

4. WARRANTIES AND DISCLAIMERS
Provider warrants that services will be performed in professional workmanlike manner. EXCEPT AS EXPRESSLY SET FORTH HEREIN, PROVIDER MAKES NO WARRANTIES.

5. LIMITATION OF LIABILITY
PROVIDER'S LIABILITY SHALL NOT EXCEED AMOUNTS PAID BY CLIENT IN THE 12 MONTHS PRECEDING THE CLAIM. IN NO EVENT SHALL PROVIDER BE LIABLE FOR CONSEQUENTIAL, INCIDENTAL, OR PUNITIVE DAMAGES.

6. INDEMNIFICATION
Each party shall indemnify the other against third-party claims arising from: (a) breach of this Agreement, (b) negligent or wrongful acts, (c) violation of law.

7. CONFIDENTIALITY
Both parties acknowledge they may receive confidential information and agree to maintain confidentiality for 3 years post-termination.

8. TERM AND TERMINATION
- Initial term: 2 years, auto-renewing annually
- Either party may terminate with 30 days written notice
- Termination for cause effective immediately
- Surviving provisions: IP, confidentiality, limitation of liability

9. FORCE MAJEURE
Neither party liable for delays due to circumstances beyond reasonable control including natural disasters, government actions, or pandemics.

10. GOVERNING LAW AND DISPUTES
This Agreement governed by New York law. Disputes resolved through binding arbitration under AAA Commercial Arbitration Rules."""

    def get_sla_sample(self):
        return """SERVICE LEVEL AGREEMENT

This Service Level Agreement ("SLA") governs the provision of cloud hosting services by CloudTech Solutions ("Provider") to Customer.

1. SERVICE DESCRIPTION
Provider will deliver managed cloud hosting services including:
- Virtual server infrastructure
- 24/7 monitoring and support
- Data backup and recovery
- Security management

2. SERVICE LEVELS AND METRICS

2.1 UPTIME AVAILABILITY
- Target: 99.9% monthly uptime
- Measurement: Total minutes per month minus downtime
- Planned maintenance excluded (with 48-hour advance notice)

2.2 RESPONSE TIMES
- Critical Issues: 1 hour acknowledgment, 4 hour resolution target
- High Priority: 2 hour acknowledgment, 8 hour resolution target  
- Medium Priority: 8 hour acknowledgment, 24 hour resolution target
- Low Priority: 24 hour acknowledgment, 72 hour resolution target

2.3 PERFORMANCE STANDARDS
- Network latency: <100ms average response time
- Data transfer: Minimum 100 Mbps sustained throughput
- CPU utilization: <80% average during peak hours

3. SERVICE CREDITS

3.1 UPTIME CREDITS
- 99.0% - 99.89% uptime: 10% monthly fee credit
- 95.0% - 98.99% uptime: 25% monthly fee credit
- Below 95.0% uptime: 50% monthly fee credit

3.2 RESPONSE TIME CREDITS
Failure to meet response time SLAs results in 5% credit per incident.

4. EXCLUSIONS
SLAs do not apply to outages caused by:
- Customer actions or configurations
- Third-party services outside Provider control
- Force majeure events
- Scheduled maintenance with proper notice
- DDoS attacks or security incidents

5. MONITORING AND REPORTING
- Real-time monitoring dashboard available 24/7
- Monthly SLA reports delivered by 5th of following month
- Incident post-mortems provided within 5 business days

6. ESCALATION PROCEDURES
Level 1: Technical support team
Level 2: Senior engineers and team lead
Level 3: Engineering management and account manager
Level 4: Executive escalation

7. SERVICE CREDIT PROCEDURE
Credits automatically applied to next monthly invoice. Customer must report SLA violations within 30 days."""

    def get_employment_sample(self):
        return """EMPLOYMENT AGREEMENT

This Employment Agreement is between InnovateCorp Inc. ("Company") and Jane Smith ("Employee").

1. POSITION AND DUTIES
Employee hired as Senior Software Engineer reporting to VP Engineering. Duties include:
- Full-stack web application development
- Code review and mentoring junior developers
- Architecture design and technical leadership
- Participation in on-call rotation

2. COMPENSATION
- Base salary: $140,000 annually
- Performance bonus: Up to 20% of base salary
- Equity grant: 2,000 stock options vesting over 4 years
- Benefits: Health, dental, vision, 401k with 4% match

3. CONFIDENTIALITY
Employee agrees to maintain confidentiality of trade secrets, customer information, and proprietary business information during and after employment.

4. INTELLECTUAL PROPERTY
All work product created during employment belongs to Company. Employee assigns all rights to inventions and discoveries made using Company resources.

5. NON-COMPETE AND NON-SOLICITATION
For 12 months post-employment, Employee agrees not to:
- Work for direct competitors in similar role
- Solicit Company employees or customers
- Use confidential information for competitive purposes

6. TERMINATION
- At-will employment for both parties
- 2 weeks notice preferred but not required
- Company may terminate immediately for cause
- Severance: 2 weeks pay if terminated without cause

7. DISPUTE RESOLUTION
Disputes resolved through binding arbitration under California Employment Dispute Resolution Act.

This Agreement governed by California law and supersedes all prior agreements."""

    def get_software_license_sample(self):
        return """SOFTWARE LICENSE AGREEMENT

This Software License Agreement ("License") governs use of DataAnalytics Pro software ("Software") provided by AnalyticsSoft Inc. ("Licensor") to Customer ("Licensee").

1. GRANT OF LICENSE
Licensor grants Licensee non-exclusive, non-transferable license to use Software solely for internal business purposes according to purchased license type.

2. LICENSE TYPES AND RESTRICTIONS

2.1 NAMED USER LICENSE
- Software may be installed on devices used by named individuals
- Maximum 5 concurrent users per license
- No sharing of login credentials

2.2 SITE LICENSE  
- Software may be used by unlimited users at single location
- Additional locations require separate site licenses
- Remote access permitted for licensed site employees

3. RESTRICTIONS
Licensee may not:
- Reverse engineer, decompile, or disassemble Software
- Modify, adapt, or create derivative works
- Distribute, rent, lease, or sublicense Software
- Remove proprietary notices or labels

4. INTELLECTUAL PROPERTY
Software contains trade secrets and copyrighted materials. Licensor retains all ownership rights.

5. WARRANTY AND SUPPORT

5.1 LIMITED WARRANTY
Licensor warrants Software will perform substantially according to documentation for 90 days. Exclusive remedy is repair or replacement.

5.2 SUPPORT SERVICES
- Standard support: Email support during business hours
- Premium support: Phone and email with 4-hour response time
- Major version upgrades included for first year

6. LIMITATION OF LIABILITY
LICENSOR'S LIABILITY LIMITED TO LICENSE FEES PAID. NO LIABILITY FOR CONSEQUENTIAL, INCIDENTAL, OR INDIRECT DAMAGES.

7. COMPLIANCE AND AUDIT
Licensor may audit compliance with license terms upon 30 days notice during normal business hours.

8. TERM AND TERMINATION
- License term: 1 year with annual renewal
- Termination for breach with 30 days cure period
- Effect of termination: Cease use and destroy copies

9. EXPORT COMPLIANCE
Software subject to U.S. export control laws. Licensee responsible for compliance with applicable regulations."""

async def main():
    """Main training function"""
    trainer = RAGTrainer()
    
    print("🤖 AI Contract Review - RAG Training System")
    print("=" * 50)
    
    try:
        results = await trainer.train_with_sample_documents()
        
        # Summary
        successful_uploads = sum(1 for r in results if r.get("status") == "success")
        total_chunks = sum(r.get("chunks_created", 0) for r in results)
        
        print(f"\n📋 Training Summary:")
        print(f"   Successfully uploaded: {successful_uploads}/5 documents")
        print(f"   Total chunks created: {total_chunks}")
        print(f"   RAG system ready for contract analysis! 🎉")
        
    except Exception as e:
        print(f"❌ Training failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())