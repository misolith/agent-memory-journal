# TODO.md

## agent-memory-journal → oikeasti toimiva long-term memory

Tämä tiedosto on repon ohjaava toteutussuunnitelma. Jatkossa tämän repon kehitystyön tulee osua tähän suunnitelmaan eikä ajautua takaisin geneeriseksi notes-CLI:ksi.

## 0. Arvio nykyisestä ehdotuksesta

Mison ehdotus on oikeansuuntainen ja korjaa juuri nykyisen arkkitehtuurivirheen:
- nykyrepo hoitaa pääosin **cold archive / audit** -kerrosta
- mutta agentin oikea tarve on kolmiosainen:
  1. **hot set** aina contextissa
  2. **warm recall** pyydettäessä
  3. **cold archive** auditointiin ja historian säilytykseen

Keskeinen korjaus on tämä:
**muistia ei saa enää mallintaa yhtenä kasana tiedostoja**, vaan kerroksellisena järjestelmänä, jossa promotion, decay, supersedes ja recall ovat ensiluokkaisia käsitteitä.

## 1. Scope decision document (ensin, ei koodia)

Ennen varsinaista arkkitehtuurirefaktoria kirjoitetaan yksi lyhyt suunnitteludokumentti, esimerkiksi `docs/scope.md`, jossa päätetään vähintään nämä:

### 1.1 Kenen muisti?
- Ensisijainen target: **yksi agentti / yksi repo / yksi operator-ympäristö**
- Ei optimoida ensin tiimi- tai multi-tenant-mallille
- Session-scope short-term memory voi olla usean subagentin jaettu, mutta pitkä muisti kuuluu yhdelle agent-identiteetille

### 1.2 Muistin kategoriat
Vakiotaksonomia ensimmäiseen versioon:
- `decision`
- `constraint`
- `gotcha`
- `preference`
- `capability`

Mahdolliset lisäkategoriat myöhemmin, mutta mitään scoringia ei tehdä ilman eksplisiittistä category-tagia.

### 1.3 Unohtamisen malli
Unohtaminen ei ole delete vaan tilasiirtymä:
- `active`
- `archived`
- `superseded`

Säännöt:
- warm/core-merkintä voi arkistoitua inaktiivisuuden vuoksi
- uusi merkintä voi korvata vanhan `supersedes: <id>`-suhteella
- cold/episodic säilytetään audit trailina

### 1.4 Threat model
Kirjoitusoikeus täytyy mallintaa eksplisiittisesti:
- `source=user`
- `source=agent`
- `source=import`
- `source=subagent`

V1 sääntö:
- episodic-kirjoitus sallittu käyttäjältä ja agentilta
- core-promotion sallittu automaatiolta sääntöjen perusteella
- AGENT.md-promotion vain pin/review-polun kautta
- subagentin kirjoitukset eivät saa nousta hot setiin ilman lisäehtoja

### Deliverable
- `docs/scope.md`
- ei koodia ennen tämän hyväksyntää

---

## 2. Target architecture: kolmikerrosmuisti

Tavoiterakenne:

```text
<root>/
├── AGENT.md
├── core/
│   ├── decisions.md
│   ├── constraints.md
│   ├── gotchas.md
│   ├── preferences.md
│   └── capabilities.md
├── episodic/
│   └── YYYY-MM-DD.md
├── index/
│   ├── manifest.json
│   └── embeddings.sqlite
└── archive/
    └── core/
```

### 2.1 Layer semantics
- `AGENT.md` = hot set, aina contextissa, tiukka kokoraja
- `core/*` = warm memory, rakenteinen ja recall-haettava
- `episodic/*` = cold raw log, append-only oletuksena
- `archive/core/*` = aktiivisesta käytöstä poistunut warm memory
- `index/*` = recallin ja eheyden apurakenteet

### 2.2 AGENT.md policy
- generoitu tiedosto, ei ensisijaisesti käsin ylläpidetty
- sisältö vain pinned + aktiivisesti relevantti core-joukko
- hard limit: **2048 chars**
- jos raja ylittyy, build/doctor epäonnistuu

### 2.3 Backward compatibility
V1 migration-polku:
- nykyinen `MEMORY.md` → splitataan kategorioihin `core/*`
- nykyinen `memory/YYYY-MM-DD.md` → siirretään `episodic/`
- vanhaa layoutia voidaan tukea import-tilassa, mutta sitä ei pidetä tavoitetilana

---

## 3. Promotion pipeline

Nykyinen `candidates/review/promote` muutetaan eksplisiittiseksi pipelineksi:

```text
episodic/raw
  -> candidate(scored, categorized)
  -> core/<category>.md
  -> AGENT.md
```

### 3.1 Candidate rules
Jokaisella candidatella tulee olla vähintään:
- stable `id`
- `category`
- normalized claim
- occurrences
- source refs
- source provenance
- score breakdown
- status (`candidate|promoted|archived|superseded`)

### 3.2 Auto-promotion: episodic → core
Ensimmäinen sääntöversio:
- promote, jos sama normalisoitu fakta esiintyy vähintään **2 eri päivänä**
- ja mukana on vähintään yksi triggeri tai eksplisiittinen muistimerkintä
- tai käyttäjä/agentti merkitsee sen eksplisiittisesti muistettavaksi (`remember:`-tag)

### 3.3 Manual promotion: core → AGENT.md
- vain review/pin-polun kautta
- ei automaattista AGENT.md-kasvua ilman tiukkaa politiikkaa
- AGENT.md:hen pääsee vain memory, joka vaikuttaa agentin jokapäiväiseen toimintaan

### 3.4 Decay / archive
- core-merkintä, jota ei ole referoitu **30 päivään**, on archive-ehdokas
- archive on palautettava, ei delete
- weekly review raportoi mitkä ovat archive-ehdokkaita

### 3.5 Supersedes
- uusi claim voi sisältää `supersedes: <id>`
- vanha ei poistu, vaan merkitään `superseded`
- recall osaa näyttää aktiivisen version ensin

---

## 4. Recall architecture

Recall tehdään kerroksittain. Ei enää pelkkä substring-haku.

### 4.1 Recall tiers
1. **exact/grep**
   - nopea path/needle-haku
   - pidetään debugiin ja yksiselitteisiin kyselyihin

2. **BM25**
   - ensimmäinen oikea ranking-kerros
   - toteutetaan ennen embeddings-tasoa
   - korjaa suurimman osan käytännön recall-ongelmista

3. **semantic recall**
   - vasta BM25:n jälkeen
   - sqlite-pohjainen indeksikerros, ei erillistä vektori-DB:tä

### 4.2 API-first interface
Python API on ensisijainen:

```python
from agent_memory import Journal
j = Journal(root='.memory')
hits = j.recall('Azure hub-spoke topology', k=5, tier='warm')
```

Palautusobjekti sisältää ainakin:
- text
- category
- tier
- source refs
- provenance
- score
- score components
- status

### 4.3 Implementation order
1. exact refactor shared search abstractioniin
2. BM25 ranking warm + episodic recalliin
3. semantic layer optional feature flagin taakse

---

## 5. Agent integration model

Tämä repo optimoidaan OpenCode/Claude Code/OpenClaw-tyyppiselle agentille, ei geneeriselle kaikille.

### 5.1 Always-context hot set
- agentti lataa `AGENT.md`:n automaattisesti contextiin
- `AGENT.md` pysyy erittäin pienenä
- tavoite: 10–20 aidosti käyttäytymiseen vaikuttavaa faktaa

### 5.2 Recall tool
Tarjotaan työkalu/API:
- `memory_recall(query, k=5, tier='warm')`

Agentti kutsuu sitä itse tarpeen mukaan, ei bulk-loadaa muistia promptiin.

### 5.3 Write tool
Tarjotaan työkalu/API:
- `memory_note(text, category, importance, source, pin=False)`

Säännöt:
- high importance → candidate promotioniin
- `pin=True` ei kirjoita suoraan AGENT.md:hen, vaan merkitsee review/pin-ehdokkaaksi

### 5.4 Session-scoped short-term memory
Lisätään session-scope:
- `sessions/<session_id>.md` tai vastaava sisäinen rakenne
- TTL = session lifecycle
- jos sama claim toistuu useassa sessiossa, siitä voi tulla core-candidate

Tämä yhdistää short-term ja long-term muistin saman rajapinnan alle ilman että ne sekoittuvat semanttisesti.

---

## 6. Anti-bloat guardrails

Nykyinen repo tarvitsee tiukat kasvurajat.

### 6.1 Hard limits
- `AGENT.md` max **2048 chars**
- `core/<category>.md` max **50 bullets per file**
- rajan ylitys → `doctor` fail tai explicit warning + required cleanup mode

### 6.2 Smarter dedupe
Nykyinen string-normalization ei riitä.

V1:
- parempi claim normalization
- duplicate detection score + rule layer

V2:
- semantic dedupe similarity thresholdilla

### 6.3 Weekly review
Lisätään:
- `digest --weekly`

Raportoi ainakin:
- mitä promotoitiin
- mitä arkistoitiin
- mitkä AGENT.md-rivit eivät ole aktivoituneet
- mitkä core-merkinnät lähestyvät decayta

---

## 7. Security hardening

### 7.1 Path validation
- reject `..`
- reject absoluuttiset polut epäluotettavista syötteistä
- root confinement kaikille write-operaatioille

### 7.2 Promotion hygiene
- blacklist / sanitize ennen AGENT.md-promotionia
- estä obvious prompt-injection payloadit
- estä zero-width/control-char -ongelmat

### 7.3 Regex safety
- trigger patternit eivät saa aiheuttaa pathological regex -ongelmia
- timeout tai turvallinen pattern-politiikka

### 7.4 Provenance enforcement
Jokaisella merkinnällä oltava:
- `source`
- `created_at`
- `refs`
- `category`

AGENT.md:hen vain:
- `source=user`
- tai auto-promoted claim, joka täyttää occurrence + review -säännöt

### 7.5 Integrity verification
- `index/manifest.json` sisältää checksummat core-tiedostoille
- `doctor --verify` havaitsee odottamattomat muutokset

---

## 8. Packaging and codebase refactor

Nykyinen yksi iso tiedosto puretaan moduleihin.

### Target module split
- `agent_memory/storage.py`
- `agent_memory/recall.py`
- `agent_memory/promote.py`
- `agent_memory/models.py`
- `agent_memory/security.py`
- `agent_memory/api.py`
- `agent_memory/cli.py`

### Prioriteetti
- Python API ensin
- CLI sen päälle
- SKILL.md myöhemmin uusiksi agentin käyttöohjeeksi, ei CLI-manuaaliksi

---

## 9. Concrete phased implementation plan

## Phase A — Define the system correctly
Deliverables:
- `docs/scope.md`
- `docs/architecture.md`
- `docs/promotion_rules.md`
- `TODO.md` päivittyy tarvittaessa

Success criterion:
- muistin kerrokset, taksonomia, decay, supersedes, provenance ja AGENT.md-politiikka ovat päätetty kirjallisesti

## Phase B — Restructure codebase around API
Deliverables:
- package layout `agent_memory/`
- existing functionality moved pois monoliitista
- compatibility shim CLI:lle

Success criterion:
- nykyiset testit toimivat uuden pakettirakenteen päällä

## Phase C — Implement three-tier storage
Deliverables:
- uusi root layout
- migration/import commands vanhasta layoutista
- core/episodic/archive/AGENT.md support

Success criterion:
- repo osaa lukea ja kirjoittaa uutta layoutia ilman backward-regressionia

## Phase D — Implement promotion pipeline
Deliverables:
- candidate model
- category tagging
- occurrence tracking
- promote-to-core rules
- pin/review path AGENT.md:lle
- supersedes and archive states

Success criterion:
- raw episodic note voi kulkea deterministisesti candidate → core → pinned hot set

## Phase E — Implement recall v2
Deliverables:
- exact recall abstraction
- BM25 retrieval
- ranked result objects
- optional semantic index scaffold feature-flagilla

Success criterion:
- recall osaa palauttaa relevantteja warm/cold osumia ilman full-scan-UX:ää

## Phase F — Guardrails and integrity
Deliverables:
- AGENT.md limit enforcement
- per-core-file limits
- doctor verify
- provenance checks
- promotion sanitization

Success criterion:
- memory growth pysyy hallittuna ja manipulointi näkyy auditissa

## Phase G — Agent integration polish
Deliverables:
- explicit Python API examples
- session-scoped memory support
- updated `SKILL.md`
- updated `README.md`

Success criterion:
- repo tuntuu agent-memoryltä eikä notes-CLI:ltä

---

## 10. Immediate next actions

Nämä tehdään seuraavaksi, tässä järjestyksessä:

1. Kirjoita `docs/scope.md`
2. Kirjoita `docs/architecture.md`
3. Kirjoita `docs/promotion_rules.md`
4. Refaktoroi monoliitti pakettirunkoon ilman behavior-muutosta
5. Lisää uusi storage layout rinnakkaistukena
6. Implementoi candidate/core/AGENT.md pipeline
7. Lisää BM25 recall
8. Lisää guardrailit ja verify-polku
9. Päivitä README + SKILL

---

## 11. Explicit non-goals for now

Ei vielä:
- LLM-summarointia core-tiedostoihin
- omaa vektori-DB:tä
- multi-tenant/team-first mallia
- täysin automaattista AGENT.md-generointia ilman review-politiikkaa
- geneeristä "works for any agent" -abstraktiota

---

## 12. Success metric

Tämä roadmap onnistuu vasta kun kaikki seuraavat pitävät yhtä aikaa paikkansa:
- `AGENT.md` sisältää noin 10–20 oikeasti toimintaa muuttavaa asiaa
- tiedostoa ei ole käsin rakennettu pääosin
- warm/core muistissa on selkeä kategorinen rakenne
- episodic/cold säilyy auditoitavana
- recall löytää relevantit asiat ilman koko historian lataamista contextiin
- memory ei enää vain kasva, vaan myös **tiivistyy, vanhenee ja korvautuu hallitusti**
