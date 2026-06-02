# YouTube Video Presentation Concept

Introducing **Aura**, the digital guardian of **carnaval**. Aura represents the core philosophy of our framework: *the art of the mask*—an elegant, secure, and reversible barrier that conceals sensitive identities while allowing systems to process the essentials.

## 🎭 Meet Aura, our Brand Ambassador

![Aura - Brand Ambassador](docs/video_mascot.png)

Aura embodies the fusion of high-security cryptography (represented by the gold and black digital mask) and modern developer experience. She will serve as the host and narrator in our video, guiding developers and enterprise architects through the pipeline.

---

## 🎬 YouTube Video Script: "The Art of the Mask"
**Duration**: ~90 seconds  
**Tone**: Premium, fast-paced, tech-focused, reassuring  
**Background Music**: Sleek electronic synth-wave, building up in intensity  

| Time | Visual / Video Action | Voiceover (Aura's voice - calm, confident) |
| :--- | :--- | :--- |
| **00:00 - 00:12** | **Intro Hook**: Black screen with neon purple lines pulsing. Aura appears in a 3D hologram style. The logo `carnaval` fades in under her. | *"In the age of cloud LLMs, sending B2B data to external API endpoints is a security gamble. How do you integrate AI without leaking client PII?"* |
| **00:12 - 00:28** | **The Problem**: Animation showing cleartext documents containing names, IBANs, and company codes rising up to a cloud and glowing red (leak danger). | *"Standard redaction ruins utility. Static masking breaks data structure. And cloud filters are too late. Developers need a local-first, reversible solution."* |
| **00:28 - 00:45** | **The Solution**: Aura gestures, and a document slides in. As it passes through a virtual mask shield, names are replaced by tags (e.g. `[SUPPLIER_1]`). | *"Meet **carnaval**. A lightweight Python library designed to mask PII locally before cloud ingestion, query any LLM safely, and restore original values back into structured outputs."* |
| **00:45 - 01:05** | **How it Works**: A quick screen recording showing the 7-Stage pipeline. We zoom in on the AES-256-GCM Vault and the 187 pytest validation suite. | *"Operating completely in RAM via a 7-stage pipeline, carnaval uses local GLiNER neural models for zero-shot detection. Mapping tables are locked locally in an encrypted AES-256-GCM vault."* |
| **01:05 - 01:20** | **E2E Demo**: Quick recording of the interactive website simulator. We show a French invoice anonymized, sent to Claude, and reinjected instantly. | *"The cloud LLM only sees non-identifying semantic tokens. Once the structured response is returned, the vault reinjects the real values back on your secure boundary."* |
| **01:20 - 01:30** | **Outro**: Aura smiles as the mask pulses. The terminal command `pip install carnaval` appears in glowing white text. Links to GitHub and docs. | *"Privacy-preserving AI integration. Lightweight, stateless, and 100% reversible. Install carnaval today and master the art of the mask."* |

---

> [!TIP]
> **Production Recommendation**
> For the voiceover, you can use a high-quality AI text-to-speech engine (like ElevenLabs) with a "professional female tech presenter" voice to match Aura's cyberpunk aesthetic.
