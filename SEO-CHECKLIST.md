# SEO Checklist (Bharat Sinha Portfolio)

## 1. Realistic expectations (important)
Nobody can guarantee a #1 rank. The plain keyword "data analyst" is dominated by job boards,
Wikipedia and big companies, so a personal site will not rank there. Target searches you CAN win:

| Search | Chance | Timeline |
|---|---|---|
| "Bharat Sinha data analyst" (your name) | Very high | 1-6 weeks after indexing |
| "data analyst Delhi NCR" / "data analyst portfolio Delhi" | Medium | 2-6 months |
| "Excel dashboard data analyst Delhi" | Medium | 2-6 months |
| "Swiggy sales analysis Excel dashboard", "hospital ER wait time analysis" | High (long-tail) | 1-3 months |
| "data analyst" | Practically none | not a goal |

## 2. Day 1 (after the site is live)
1. Google Search Console: add property, choose "URL prefix", use your live site URL.
2. Verify: copy the content value of the meta tag Google gives you, paste it in the admin panel
   (Profile tab, "Google Search Console verification code"), Publish, then click Verify.
3. Sitemaps, submit `sitemap.xml`.
4. URL Inspection, paste the home page and both case-study URLs, click "Request indexing".
5. Bing Webmaster Tools: sign in and "Import from Google Search Console".
6. Check https://search.google.com/test/rich-results with your home URL (Person/ProfilePage).

## 3. Week 1-4: links and identity (this is what actually moves rankings)
- Put the site URL on LinkedIn (Contact info, Website + Featured section), GitHub profile (website field),
  LeetCode profile.
- In each GitHub project README, link to the matching case-study page on your site.
- Use the same name and title everywhere: "Bharat Sinha", "Data Analyst", "Delhi NCR".
- Post each case study as a short article (LinkedIn, Medium or dev.to) with a link back to the case page.
- Real dashboard screenshots are already on the site. For each new project, upload a screenshot in the admin panel
  (Projects tab, "Image"); it is resized to 1600px and 960px automatically. Fill the "Image description" field: it is
  your alt text, which helps Google Images and screen readers.

## 4. Monthly
- Add 1 new project in the admin panel (it creates a new indexable case-study page automatically).
  Fill Problem, Approach, Impact and Key numbers with real, specific results.
- Check Search Console, Performance: which queries show impressions, then improve those pages.

## 5. Optional but strong: custom domain
A domain like bharatsinha.in builds a brand and is easy to remember.
Add a file named `CNAME` (content: `www.yourdomain.in`) to the repo root and set the DNS records
GitHub shows in Settings, Pages. The build script picks the domain up automatically
(canonical, sitemap and robots update by themselves).

## 6. Do not
- Keyword stuffing, hidden text, buying backlinks or copying text from other sites.
- Claiming results or numbers that are not real.

## What the site already does for you
Keyword-first title and description, one h1 per page, canonical URLs, sitemap + robots, JSON-LD
(WebSite, Person, ProfilePage, Article, Breadcrumb), FAQ and case-study pages, favicons, 404 page,
Open Graph/Twitter cards, static HTML that Google can read without JavaScript, and an auto-built
sitemap on every publish.
