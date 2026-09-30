# DocNexus AI — Commercialization

---

## Target Users

| Segment | Use Case |
|---|---|
| **Legal teams** | Contract analysis, clause search, obligation extraction (aligns with CUAD dataset) |
| **Universities** | Research paper management, literature search, academic document QA |
| **SMEs** | Policy, HR, and compliance document retrieval and Q&A |
| **Research teams** | Technical document intelligence and cross-document evidence retrieval |
| **HR departments** | Employee handbook search, onboarding document QA |

---

## Target Market

- **Primary**: Legal-tech and document-intensive businesses in South Asia and globally
- **Secondary**: Higher education institutions requiring document intelligence tooling
- **Tertiary**: Government and NGO organizations managing large document repositories

**Market size**: The global intelligent document processing market is estimated at USD 1.5 billion (2024) growing at ~30% CAGR.

---

## Pricing Strategy

### Free Tier
- Up to 10 document uploads
- Up to 50 AI queries per month
- Basic retrieval (semantic only)
- Community support

### Pro — USD 29/month per user
- Up to 500 document uploads
- Unlimited AI queries
- Hybrid retrieval (semantic + BM25)
- Citation-verified answers
- Email support

### Team — USD 99/month (up to 10 users)
- Everything in Pro
- Shared document workspaces
- Document permission management
- Priority support

### Enterprise — Custom pricing
- Unlimited documents and users
- On-premise or private cloud deployment
- Custom LLM model configuration
- SLA and dedicated support
- API access for system integration

---

## Deployment Model

### Cloud (MVP)
- Backend: FastAPI on a managed container service (e.g., Google Cloud Run, AWS ECS)
- Database: MongoDB Atlas (managed)
- Vector store: ChromaDB persistent volume
- LLM: Google Gemini API (pay-per-token)
- Frontend: Static hosting (Vercel, Netlify, or Cloud CDN)

### On-Premise (Enterprise)
- Containerised via Docker Compose
- Local MongoDB replica set
- Local ChromaDB volume mount
- Configurable LLM provider (swap Gemini for local models if required)

---

## Competitive Advantages

1. **Evidence-only answers** — the system never invents answers; it abstains when evidence is insufficient
2. **Page-level citations** — every claim links to a specific document page
3. **Hybrid retrieval** — combines semantic and keyword search for better recall
4. **Multi-agent transparency** — each processing step is visible and explainable
5. **Privacy by design** — per-user document isolation enforced at the database level

---

## Responsible AI Commitment

DocNexus AI is designed with Responsible AI principles embedded in the core pipeline:

- Hallucination is controlled at the architecture level, not as a post-hoc filter
- All NLP techniques (NER, summarization, classification) are explainable and rule-based
- Source attribution is server-side and cannot be spoofed by document content
- User data is isolated per account with no cross-user data leakage

This makes DocNexus AI suitable for regulated industries such as legal, healthcare, and finance where auditability and explainability are mandatory.
