Agent Readiness
Things that make a site legible to AI agents and crawlers.


Agent readiness
Recommended
Agent readiness is the set of choices that make a site legible to AI agents and LLMs: stable URLs, structured data, clean semantics, robots controls, and machine-readable endpoints.


/llms.txt
Recommended
A proposed markdown file at the site root that gives LLMs a curated index of your most important content. Emerging convention, not a ratified standard.


/llms-full.txt
Optional
An extended companion to /llms.txt that concatenates the full markdown content of your key pages into a single file. Useful for small sites, costly for large ones.


Per-page Markdown source endpoints
Recommended
Expose every documentation page's raw Markdown source at a predictable URL — via a .md suffix on the canonical URL, content negotiation, or both. Agents pull source instead of parsing HTML.


robots.txt for AI crawlers
Recommended
Major AI vendors publish named user-agents for their crawlers. Setting an explicit allow or disallow per agent is the clearest way to control how your content is used.


Content Signals in robots.txt
Optional
Add Content-Signal directives to robots.txt to declare whether AI crawlers may search, ingest, or train on your content. An emerging IETF AI Preferences / IAB Tech Lab proposal that some validators already check.


Web Bot Auth — verifiable bot identity
Optional
Web Bot Auth lets a bot prove who it is by signing each HTTP request with a key it controls. Sites can then allow or block specific bots without IP allow-lists, user-agent strings, or guesswork. Built on RFC 9421 HTTP Message Signatures.


Stable URLs
Required
URLs are public contracts. Once published, they should keep working. Breaking them invalidates citations, bookmarks, links, and agent caches — and is almost always avoidable.


Structured data for agents
Recommended
JSON-LD with schema.org types gives agents typed facts about your page. It is the same markup search engines use, and agents lean on it just as heavily.


Machine-readable formats
Recommended
Offer JSON, RSS, or plain markdown endpoints alongside HTML where it makes sense. Agents and feed readers prefer typed data over scraped HTML.


HTTP Link headers for discovery
Recommended
Use the HTTP Link header to advertise machine-readable resources — llms.txt, sitemap, api-catalog, RSS — directly in the response. Agents that never parse your HTML can still find what they need.


MCP and tool discovery
Optional
The Model Context Protocol is an emerging way for sites to expose queryable tools to agents over JSON-RPC. Relevant whenever your content has structure worth filtering — even for a static reference site like this one.


A2A agent cards
Optional
The Agent-to-Agent (A2A) protocol lets an autonomous agent find another autonomous agent and call it over JSON-RPC. Discovery hinges on a single well-known file: `/.well-known/agent-card.json`. Relevant whenever your service exposes agentic behaviour another agent might want to delegate to.


Agent Skills discovery
Recommended
A well-known URI that lists Agent Skills — short, scoped instructions an AI agent can load to work better with your site. Emerging convention via a Cloudflare-led RFC; still draft, still cheap to ship.


DNS for AI Discovery (DNS-AID)
Optional
Publish SVCB/HTTPS records under _agents.example.com so agents can discover your services from DNS, before any HTTP round-trip. Pair with DNSSEC so the answer is authenticated.


Agentic Resource Discovery (ARD)
Optional
Publish an AI Catalog at /.well-known/ai-catalog.json listing the agent capabilities your domain offers — MCP servers, A2A agents — so registries and agents can find and trust them from one fetch.


NLWeb — conversational interface discovery
Optional
NLWeb is an emerging convention for exposing a site as a conversational AI endpoint. A site advertises an `/ask`-style endpoint via a `rel="nlweb"` link and serves an MCP-compatible JSON-RPC interface that agents can query in natural language.


WebMCP — browser-native tools for agents
Optional
WebMCP lets a page register tools that an in-browser AI agent can call directly, using a `navigator.modelContext` JavaScript API. It turns a site into an agent surface without server-side MCP plumbing.


Open Knowledge Format (OKF) bundle
Optional
Publish your whole knowledge base as an Open Knowledge Format bundle — a tree of Markdown concept files with typed front matter — so an agent can ingest the entire corpus in one fetch instead of scraping page by page.


Schemamap — discoverable JSON-LD endpoints per resource
Optional
A convention this site proposes — no external standard exists yet. `/schemamap.xml` indexes one JSON-LD endpoint per resource so agents fetch the structured-data graph directly instead of extracting it from HTML.
