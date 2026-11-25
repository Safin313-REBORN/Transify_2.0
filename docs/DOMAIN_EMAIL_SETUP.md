# Transify 2.0 — Custom Domain Email Setup Guide (`transify.nexus`)

This guide provides the complete DNS record configuration for setting up official domain email routing (`support@transify.nexus` and `contact@transify.nexus`).

---

## 1. Domain DNS Records Table

Add the following DNS records at your domain registrar or DNS provider (Cloudflare, Namecheap, Google Domains, etc.):

### A. MX Records (Mail Exchange)
Choose your preferred mail provider:

#### Option 1: Cloudflare Email Routing (Free, instant forwarding to developer Gmail)
| Type | Host / Name | Value | Priority | TTL |
| :--- | :--- | :--- | :--- | :--- |
| `MX` | `@` | `isaac.mx.cloudflare.net` | `17` | Auto |
| `MX` | `@` | `linda.mx.cloudflare.net` | `56` | Auto |
| `MX` | `@` | `amir.mx.cloudflare.net` | `97` | Auto |

*Forwarding destination: `support@transify.nexus` → `safin.reborn@gmail.com`*

#### Option 2: Google Workspace
| Type | Host / Name | Value | Priority | TTL |
| :--- | :--- | :--- | :--- | :--- |
| `MX` | `@` | `ASPMX.L.GOOGLE.COM.` | `1` | 3600 |
| `MX` | `@` | `ALT1.ASPMX.L.GOOGLE.COM.` | `5` | 3600 |
| `MX` | `@` | `ALT2.ASPMX.L.GOOGLE.COM.` | `5` | 3600 |
| `MX` | `@` | `ALT3.ASPMX.L.GOOGLE.COM.` | `10` | 3600 |
| `MX` | `@` | `ALT4.ASPMX.L.GOOGLE.COM.` | `10` | 3600 |

---

### B. SPF Record (Sender Policy Framework)
Prevents email spoofing by authorizing your mail servers:
| Type | Host / Name | Value | TTL |
| :--- | :--- | :--- | :--- |
| `TXT` | `@` | `v=spf1 include:_spf.mx.cloudflare.net include:_spf.google.com ~all` | 3600 |

---

### C. DKIM Record (DomainKeys Identified Mail)
Cryptographically signs outbound emails to guarantee authenticity:
| Type | Host / Name | Value | TTL |
| :--- | :--- | :--- | :--- |
| `TXT` | `google._domainkey` | `v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0...` | 3600 |

*(Obtain exact RSA public key string from your Google Workspace or Cloudflare admin dashboard)*

---

### D. DMARC Policy Record
Enforces delivery policy and enables aggregate feedback reporting:
| Type | Host / Name | Value | TTL |
| :--- | :--- | :--- | :--- |
| `TXT` | `_dmarc` | `v=DMARC1; p=quarantine; rua=mailto:dmarc-reports@transify.nexus; pct=100; adkim=r; aspf=r` | 3600 |

---

## 2. Active Application Endpoints
The Transify 2.0 application connects with this domain email infrastructure via:
1. **Public Floating Support Link**: `mailto:support@transify.nexus`
2. **Instant Developer Feedback API**: `POST /api/contact`
3. **Structured Data ContactPoint**: Defined in Schema.org JSON-LD header
4. **WhatsApp Support Integration**: `https://wa.me/8801700000000`

---

## 3. Verification Commands
Verify DNS propagation in your terminal:
```bash
dig transify.nexus MX +short
dig transify.nexus TXT +short
dig _dmarc.transify.nexus TXT +short
```
