#!/usr/bin/env python3
"""
Complete Contract Training for All Dropdown Types
Adds training for the 5 missing contract types with no duplicated content
"""

import asyncio
import os
from services.pinecone_rag_service import PineconeRAGService

class CompleteContractTrainer:
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
    
    async def add_missing_contract_types(self):
        """Add training documents for the 5 missing contract types from dropdown"""
        print("🚀 Adding Missing Contract Types to RAG Training...")
        
        # Check initial state
        initial_vectors = await self.get_index_stats()
        print(f"📊 Current vectors in database: {initial_vectors}")
        
        # Missing contract types from dropdown that need training
        missing_contracts = [
            {
                "filename": "saas_terms_of_service.txt",
                "contract_type": "SaaS",
                "jurisdiction": "US-CA",
                "text": self.get_saas_terms_sample()
            },
            {
                "filename": "consulting_agreement.txt", 
                "contract_type": "Consulting",
                "jurisdiction": "US-NY",
                "text": self.get_consulting_agreement_sample()
            },
            {
                "filename": "purchase_agreement.txt",
                "contract_type": "Purchase", 
                "jurisdiction": "US-TX",
                "text": self.get_purchase_agreement_sample()
            },
            {
                "filename": "lease_agreement.txt",
                "contract_type": "Lease",
                "jurisdiction": "US-CA", 
                "text": self.get_lease_agreement_sample()
            },
            {
                "filename": "partnership_agreement.txt",
                "contract_type": "Partnership",
                "jurisdiction": "US-DE",
                "text": self.get_partnership_agreement_sample()
            }
        ]
        
        # Upload all missing contract types
        results = []
        for doc in missing_contracts:
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

    def get_saas_terms_sample(self):
        """SaaS Terms of Service - Unique content for cloud software platforms"""
        return """SAAS TERMS OF SERVICE

These Terms of Service ("Terms") govern your access to and use of CloudWorkspace Pro ("Service") provided by TechSolutions Inc. ("Company").

1. SERVICE DESCRIPTION
CloudWorkspace Pro is a cloud-based productivity platform providing:
- Real-time document collaboration tools
- Project management workflows  
- Video conferencing and screen sharing
- File storage and backup services
- Third-party application integrations

2. SUBSCRIPTION AND BILLING

2.1 SUBSCRIPTION PLANS
- Starter Plan: $9/user/month, up to 10 users
- Professional Plan: $19/user/month, unlimited users
- Enterprise Plan: $39/user/month, advanced security features
- Annual subscriptions receive 15% discount

2.2 BILLING TERMS
- Subscriptions billed monthly in advance
- Auto-renewal unless cancelled 30 days prior
- No refunds for partial months
- Price changes with 60 days advance notice

3. ACCEPTABLE USE POLICY
Users agree NOT to:
- Upload malicious code, viruses, or harmful content
- Share login credentials with unauthorized persons
- Reverse engineer or attempt to extract source code
- Use Service to store illegal or copyrighted material without permission
- Exceed reasonable bandwidth or storage limits

4. DATA PRIVACY AND SECURITY

4.1 DATA OWNERSHIP
Customer retains all rights to Customer Data uploaded to Service. Company claims no ownership rights over Customer Data.

4.2 DATA PROCESSING
Company processes Customer Data solely to provide Service. Data encrypted at rest and in transit using industry-standard protocols.

4.3 DATA EXPORT AND DELETION
Customers may export data in standard formats. Upon termination, data deleted within 30 days unless legally required to retain.

5. SERVICE AVAILABILITY
- Target uptime: 99.5% monthly availability
- Scheduled maintenance with 24-hour notice
- Service credits: 5% monthly fee for each 1% below 99% uptime
- Excludes downtime from customer actions or force majeure

6. LIMITATION OF LIABILITY
COMPANY'S TOTAL LIABILITY SHALL NOT EXCEED AMOUNTS PAID BY CUSTOMER IN THE 12 MONTHS PRECEDING THE CLAIM. COMPANY DISCLAIMS ALL WARRANTIES EXCEPT AS EXPRESSLY PROVIDED HEREIN.

7. ACCOUNT TERMINATION
- Either party may terminate with 30 days written notice
- Immediate termination for material breach
- Post-termination: data access for 30 days, then permanent deletion
- Outstanding fees remain due upon termination

8. MODIFICATIONS
Company may modify these Terms with 30 days advance notice. Continued use constitutes acceptance of modified Terms.

9. GOVERNING LAW
These Terms governed by California law. Disputes resolved through binding arbitration in San Francisco County."""

    def get_consulting_agreement_sample(self):
        """Consulting Agreement - Unique professional services content"""
        return """CONSULTING AGREEMENT

This Consulting Agreement ("Agreement") is between Strategic Business Advisors LLC ("Consultant") and GrowthCorp Inc. ("Client").

1. CONSULTING SERVICES
Consultant will provide strategic business consulting services including:
- Market research and competitive analysis
- Financial modeling and forecasting
- Operational efficiency assessments  
- Digital transformation strategy development
- Executive coaching and leadership development

2. ENGAGEMENT TERMS

2.1 PROJECT TIMELINE
- Phase 1: Assessment and discovery (4 weeks)
- Phase 2: Strategy development (6 weeks) 
- Phase 3: Implementation planning (4 weeks)
- Total engagement duration: 14 weeks

2.2 DELIVERABLES
- Comprehensive market analysis report
- 5-year financial projection model
- Operational improvement recommendations
- Digital transformation roadmap
- Monthly executive briefings

3. COMPENSATION STRUCTURE

3.1 PROFESSIONAL FEES  
- Hourly rate: $350 for senior consultants
- Hourly rate: $200 for junior consultants
- Project management fee: $5,000 flat rate
- Success bonus: 2% of documented cost savings achieved

3.2 EXPENSE REIMBURSEMENT
Client reimburses reasonable expenses including travel, accommodation, and research costs. Pre-approval required for expenses exceeding $500.

4. PROFESSIONAL STANDARDS
Consultant warrants:
- Services performed with professional competence
- Compliance with applicable industry standards
- Use of qualified personnel with relevant experience
- Maintenance of professional liability insurance ($2M minimum)

5. CONFIDENTIALITY OBLIGATIONS
Both parties acknowledge access to sensitive information and agree to:
- Maintain strict confidentiality for 5 years post-engagement
- Use confidential information solely for engagement purposes
- Return all materials upon completion or termination
- Notify other party immediately of any unauthorized disclosure

6. INDEPENDENT CONTRACTOR RELATIONSHIP
Consultant is independent contractor, not employee. Client not responsible for:
- Payroll taxes or employee benefits
- Workers' compensation coverage
- Providing office space or equipment
- Controlling methods or manner of work performance

7. INTELLECTUAL PROPERTY OWNERSHIP
- Pre-existing IP remains with original owner
- Custom methodologies developed jointly owned
- Final deliverables and recommendations owned by Client
- Consultant retains right to use general knowledge and experience

8. PERFORMANCE GUARANTEES
Consultant guarantees:
- Deliverables completed on schedule unless Client delays
- Work product meets professional standards
- Key personnel assigned remain on project unless unavailable
- Regular progress reporting and communication

9. TERMINATION PROVISIONS
- Either party may terminate with 14 days written notice
- Client pays for work completed through termination date
- Consultant delivers all completed work product
- Post-termination confidentiality obligations survive"""

    def get_purchase_agreement_sample(self):
        """Purchase Agreement - Unique commercial transaction content"""  
        return """ASSET PURCHASE AGREEMENT

This Asset Purchase Agreement ("Agreement") is between Industrial Manufacturing Corp. ("Seller") and AcquireTech Holdings LLC ("Buyer").

1. PURCHASED ASSETS
Buyer agrees to purchase the following business assets:
- Manufacturing equipment and machinery (Schedule A)
- Inventory and raw materials (Schedule B) 
- Customer contracts and relationships (Schedule C)
- Intellectual property and trade secrets (Schedule D)
- Business name and goodwill

2. PURCHASE PRICE AND PAYMENT TERMS

2.1 TOTAL CONSIDERATION
- Base purchase price: $2,750,000
- Inventory adjustment: Fair market value at closing
- Working capital adjustment: $150,000 target
- Earnout payments: Up to $500,000 over 3 years based on revenue targets

2.2 PAYMENT SCHEDULE
- Cash at closing: $2,000,000
- Seller financing note: $750,000 over 5 years at 6% interest
- Escrow holdback: $200,000 for 18 months (indemnification claims)

3. REPRESENTATIONS AND WARRANTIES

3.1 SELLER REPRESENTATIONS
Seller represents and warrants that:
- Full legal ownership of all purchased assets
- Assets free from liens, encumbrances, and security interests
- No pending litigation affecting the business
- Financial statements fairly present business condition
- All tax obligations current and properly filed

3.2 BUYER REPRESENTATIONS  
Buyer represents and warrants that:
- Corporate authority to enter transaction
- Sufficient financing secured for purchase price
- No conflicts with existing agreements
- Due diligence investigation completed satisfactorily

4. CLOSING CONDITIONS

4.1 CONDITIONS PRECEDENT
Closing subject to:
- Completion of environmental site assessment
- Transfer of all required licenses and permits
- Key customer contract assignments executed
- Third-party lender financing approval
- No material adverse changes to business

4.2 CLOSING DELIVERIES
At closing, parties will deliver:
- Bills of sale and assignment documents
- Updated schedules of assets and liabilities
- Certificates of good standing
- Evidence of insurance coverage
- Non-compete agreements from key employees

5. POST-CLOSING COVENANTS

5.1 SELLER OBLIGATIONS
For 24 months post-closing, Seller agrees to:
- Non-compete within 100-mile radius
- Non-solicitation of customers and employees  
- Consulting availability for business transition
- Cooperation with tax audits and legal proceedings

5.2 BUYER OBLIGATIONS
Buyer agrees to:
- Assume specified contracts and obligations
- Retain key employees for minimum 12 months
- Maintain product quality and service standards
- Honor existing customer warranties

6. INDEMNIFICATION

6.1 MUTUAL INDEMNIFICATION
Each party indemnifies the other against losses from:
- Breach of representations, warranties, or covenants
- Pre-closing liabilities (Seller) / Post-closing liabilities (Buyer)
- Third-party claims related to respective periods

6.2 INDEMNIFICATION LIMITS
- Minimum claim threshold: $25,000
- Maximum liability cap: $500,000 (general claims)
- No cap for fraud, criminal acts, or environmental liabilities
- Claims must be asserted within 18 months of closing

7. DISPUTE RESOLUTION
Disputes resolved through binding arbitration under American Arbitration Association Commercial Rules in Dallas, Texas."""

    def get_lease_agreement_sample(self):
        """Lease Agreement - Unique commercial real estate content"""
        return """COMMERCIAL LEASE AGREEMENT

This Lease Agreement ("Lease") is between Metropolitan Properties Inc. ("Landlord") and Innovative Tech Solutions LLC ("Tenant").

1. LEASED PREMISES
Landlord leases to Tenant approximately 8,500 square feet of office space located at:
- Address: 1250 Technology Boulevard, Suite 400, Austin, TX 78701
- Building amenities: Lobby reception, conference facilities, parking garage
- Floor plan: Open workspace, 6 private offices, conference room, kitchen area

2. LEASE TERM AND RENT

2.1 INITIAL TERM
- Lease term: 7 years commencing January 1, 2024
- Rent commencement: March 1, 2024 (2-month improvement period)
- Renewal options: Two (2) 5-year extensions at fair market rent

2.2 BASE RENT SCHEDULE
- Years 1-2: $28 per square foot annually ($238,000/year)
- Years 3-4: $30 per square foot annually ($255,000/year)  
- Years 5-7: $32 per square foot annually ($272,000/year)
- Monthly payments due first of each month

2.3 ADDITIONAL CHARGES
- Common area maintenance (CAM): $4.50 per square foot annually
- Property taxes: Tenant's proportionate share (12.3% of building)
- Insurance: Building insurance allocated proportionately
- Utilities: Tenant responsible for separately metered usage

3. SECURITY DEPOSIT AND GUARANTY
- Security deposit: $45,000 (equal to 2 months base rent)
- Letter of credit acceptable in lieu of cash deposit
- Personal guaranty required from Tenant's principals
- Deposit returned within 60 days after lease termination

4. PERMITTED USE AND RESTRICTIONS

4.1 PERMITTED USES
Premises may be used for:
- General office and administrative operations
- Software development and technical services
- Client meetings and presentations  
- Training and educational activities

4.2 PROHIBITED USES
Tenant may not use premises for:
- Manufacturing or heavy industrial activities
- Food service or restaurant operations
- Retail sales to general public
- Activities generating hazardous materials

5. TENANT IMPROVEMENTS

5.1 INITIAL IMPROVEMENTS
- Landlord improvement allowance: $40 per square foot ($340,000 total)
- Tenant responsible for costs exceeding allowance
- Improvements must comply with building standards
- Landlord approval required for all plans and specifications

5.2 FUTURE ALTERATIONS
- Alterations over $25,000 require Landlord consent
- Tenant must obtain all required permits
- Work performed by Landlord-approved contractors
- Tenant provides certificates of insurance for all work

6. MAINTENANCE AND REPAIRS

6.1 LANDLORD RESPONSIBILITIES
Landlord maintains:
- Building structure and common areas
- HVAC, plumbing, and electrical systems (excluding Tenant improvements)
- Exterior windows and building envelope
- Parking areas and landscaping

6.2 TENANT RESPONSIBILITIES  
Tenant maintains:
- Interior of premises in good condition
- Tenant improvement systems and equipment
- Regular cleaning and janitorial services
- Compliance with health and safety regulations

7. INSURANCE REQUIREMENTS

7.1 TENANT INSURANCE
Tenant must maintain:
- Commercial general liability: $2,000,000 per occurrence
- Property insurance covering Tenant's personal property
- Workers' compensation as required by law
- Business interruption insurance recommended

7.2 INDEMNIFICATION
Tenant indemnifies Landlord against claims arising from:
- Tenant's use and occupancy of premises
- Negligent acts of Tenant, employees, or invitees
- Violations of law or lease provisions

8. DEFAULT AND REMEDIES

8.1 EVENTS OF DEFAULT
Default occurs upon:
- Failure to pay rent within 10 days after written notice
- Material breach of lease terms after 30-day cure period
- Assignment for benefit of creditors or bankruptcy filing
- Abandonment of premises for 30 consecutive days

8.2 LANDLORD REMEDIES
Upon default, Landlord may:
- Terminate lease and regain possession
- Accelerate rent and collect damages
- Re-let premises and collect deficiency
- Exercise any other legal or equitable remedies"""

    def get_partnership_agreement_sample(self):
        """Partnership Agreement - Unique business collaboration content"""
        return """LIMITED LIABILITY PARTNERSHIP AGREEMENT

This Partnership Agreement ("Agreement") establishes GreenTech Innovations LLP ("Partnership") between Sarah Chen ("Partner A") and Michael Rodriguez ("Partner B").

1. PARTNERSHIP PURPOSE AND BUSINESS
The Partnership is formed to conduct the business of:
- Renewable energy consulting and project development
- Solar and wind power system design and installation
- Energy efficiency auditing for commercial properties
- Government grant application assistance for clean energy projects
- Training and certification programs for green technology professionals

2. PARTNERSHIP CONTRIBUTIONS

2.1 INITIAL CAPITAL CONTRIBUTIONS
- Partner A: $150,000 cash + $50,000 equipment (total: $200,000)
- Partner B: $100,000 cash + $100,000 client relationships (total: $200,000)
- Total initial capitalization: $400,000

2.2 ADDITIONAL CONTRIBUTIONS
Additional capital required by unanimous consent. Partners contribute proportionally to ownership percentages or risk dilution of interest.

3. OWNERSHIP AND PROFIT DISTRIBUTION

3.1 OWNERSHIP PERCENTAGES
- Partner A: 50% ownership interest
- Partner B: 50% ownership interest
- Ownership may adjust based on additional contributions

3.2 PROFIT AND LOSS ALLOCATION
- Quarterly profit distributions based on ownership percentages
- Tax losses allocated proportionally for pass-through treatment
- Retained earnings reinvested with partner approval

4. MANAGEMENT AND DECISION MAKING

4.1 MANAGEMENT STRUCTURE
- Partner A: Managing Partner (operations, finance, HR)
- Partner B: Business Development Partner (sales, marketing, client relations)
- Major decisions require unanimous consent of both partners

4.2 UNANIMOUS CONSENT REQUIRED FOR:
- Borrowing exceeding $50,000
- Capital expenditures over $25,000
- Hiring employees with salary exceeding $75,000
- Entering contracts with terms longer than 2 years
- Adding new partners or selling partnership interests

5. PARTNER DUTIES AND RESTRICTIONS

5.1 TIME COMMITMENT
Each partner agrees to:
- Dedicate full business time and attention to Partnership
- Work minimum 40 hours per week on Partnership business
- Not engage in competing business activities
- Maintain professional licenses and certifications

5.2 CONFIDENTIALITY AND NON-COMPETE
Partners agree to:
- Maintain confidentiality of Partnership information
- Non-compete for 2 years in 50-mile radius if departing
- Non-solicitation of Partnership employees and clients
- Protection of trade secrets and proprietary methodologies

6. FINANCIAL MANAGEMENT

6.1 ACCOUNTING AND RECORDS
- Annual financial statements prepared by certified accountant
- Monthly financial reports provided to all partners  
- Partnership books maintained at principal place of business
- Banking relationships require both partners' signatures

6.2 PARTNER COMPENSATION
- Partner A: Annual draw of $80,000 plus profit distributions
- Partner B: Annual draw of $80,000 plus profit distributions
- Draws reviewed annually and adjusted by mutual agreement

7. PARTNER WITHDRAWAL AND DISSOLUTION

7.1 VOLUNTARY WITHDRAWAL
Partner may withdraw with:
- 90 days written notice to other partner
- Completion of current client commitments
- Non-compete period begins immediately upon withdrawal

7.2 INVOLUNTARY WITHDRAWAL
Partner may be expelled for:
- Material breach of Partnership agreement
- Conviction of felony or professional misconduct
- Permanent disability preventing performance of duties
- Unanimous vote of remaining partners required

7.3 VALUATION AND BUYOUT
- Partnership valued by certified business appraiser
- Departing partner receives proportionate share of net worth
- Payment terms: 25% at closing, 75% over 36 months at 6% interest
- Non-compete agreement required for full payment

8. DISPUTE RESOLUTION

8.1 MEDIATION REQUIREMENT
All disputes first submitted to binding mediation under American Arbitration Association rules.

8.2 ARBITRATION
Unresolved disputes decided by binding arbitration. Arbitrator selected jointly or appointed by AAA.

9. PARTNERSHIP DISSOLUTION
Partnership dissolves upon:
- Mutual agreement of all partners
- Expiration of partnership term (if specified)
- Death or permanent incapacity of partner
- Bankruptcy or insolvency of Partnership

10. GOVERNING LAW
This Agreement governed by Delaware Limited Liability Partnership Act and Delaware state law."""

async def main():
    """Main training function for missing contract types"""
    trainer = CompleteContractTrainer()
    
    print("🤖 AI Contract Review - Complete Contract Type Training")
    print("=" * 60)
    print("📋 Training the 5 missing contract types from dropdown:")
    print("   • SaaS Terms of Service")
    print("   • Consulting Agreement")  
    print("   • Purchase Agreement")
    print("   • Lease Agreement")
    print("   • Partnership Agreement")
    print("=" * 60)
    
    try:
        results = await trainer.add_missing_contract_types()
        
        # Summary
        successful_uploads = sum(1 for r in results if r.get("status") == "success")
        total_chunks = sum(r.get("chunks_created", 0) for r in results)
        
        print(f"\n📋 Complete Training Summary:")
        print(f"   Successfully uploaded: {successful_uploads}/5 new contract types")
        print(f"   Total new chunks created: {total_chunks}")
        print(f"   🎉 All dropdown contract types now trained!")
        print(f"\n✅ RAG system ready for comprehensive contract analysis!")
        
    except Exception as e:
        print(f"❌ Training failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())