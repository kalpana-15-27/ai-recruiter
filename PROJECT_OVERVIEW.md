# AI Recruiter Pro

A full-stack AI-powered recruitment platform with **Candidate** and **Admin** portals.

## Live App
Open `frontend/index.html` directly in any browser (desktop or mobile) — it's a fully self-contained client-side app (no server required). All data is stored securely in the browser's localStorage.

## Features

### Candidate Portal
- Sign up / sign in with email or simulated Google account
- Email verification (OTP-style code) on signup
- Browse & search job postings
- Apply with resume upload (PDF / DOCX / TXT — real text extraction & skill matching)
- Track application status: Pending, Reviewed, Selected, Rejected
- In-app + real email notifications on status changes

### Admin Portal
- Restricted login — default super admin: `kalpana150906@gmail.com`
- Super admins can grant admin access to other users
- Post/deactivate job listings
- View all candidates & applications, download resumes
- Update application status (candidate gets notified automatically)
- AI-assisted match scoring, skill-gap analysis, interview question generation
- Analytics dashboard (charts, selection rate, top candidates)
- Email Provider settings (EmailJS) — connect once to send real emails from any device

## Tech Stack
- **Frontend**: React (via CDN/Babel standalone), Chart.js, pdf.js, mammoth.js, EmailJS — single `index.html`, fully responsive (desktop + mobile)
- **Backend (reference/optional)**: FastAPI + SQLAlchemy + SQLite implementation included under `backend/` for teams that want a traditional server-backed version instead of the client-side build

## Real Email Sending
The client-side app cannot call server-side email APIs directly, so real email delivery is handled via **EmailJS** (https://www.emailjs.com):
1. Create a free EmailJS account and connect your Gmail as an Email Service.
2. Create an Email Template with `to_email`, `subject`, `message` variables.
3. In the Admin Portal → Email Log page, paste your **Public Key**, **Service ID**, and **Template ID**.
4. From then on, verification codes, new-application alerts, and status-change emails send for real.

Until configured, all emails are logged in-app under Admin → Email Log (demo mode) so nothing is lost.

## Deployment
This is a static single-file app — deploy anywhere that serves static files (GitHub Pages, Netlify, Vercel, S3, etc.) or simply open `frontend/index.html` locally.

## Owner
Kalpana — kalpana150906@gmail.com
