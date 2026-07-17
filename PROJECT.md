# ☕ CofiNet+

## Project Vision

CofiNet+ is a premium captive portal designed for coffee shops, coworking spaces, hotels, and commercial establishments.

The goal is to provide a modern user experience where customers can:

- Access WiFi using a membership.
- Purchase internet access.
- Redeem a PIN code.
- Manage subscriptions.
- Receive promotions.
- Connect automatically after payment.

The experience should feel closer to Apple, Stripe or Notion than to a traditional captive portal.

---

# Main Objectives

- Premium UI/UX
- Responsive Design
- High Performance
- Clean Architecture
- Easy Scalability
- Secure Authentication
- Modern Backend

---

# Tech Stack

## Frontend

- HTML5
- TailwindCSS
- Vanilla JavaScript
- Lucide Icons

## Backend

- Python
- FastAPI

## Database

- PostgreSQL

## Authentication

- JWT

## Payments

- Stripe
- Mercado Pago

## Hosting

Frontend:
- Vercel

Backend:
- Ubuntu VPS
- Nginx

---

# Folder Structure

frontend/

    index.html

    css/

        styles.css

    js/

        app.js

        login.js

        payment.js

        animations.js

    assets/

        logo/

        images/

backend/

    app/

        main.py

        routers/

        services/

        models/

        database/

        auth/

docs/

README.md

PROJECT.md

ROADMAP.md

API.md

DATABASE.md

---

# Design Principles

The interface must be:

Elegant

Minimal

Modern

Premium

Fast

No unnecessary effects.

Animations must be subtle.

Colors:

Primary Background:

#0D0D0D

Cards:

#161616

Accent:

#A3A375

Hover:

#8C8C5E

---

# User Flow

Landing

↓

Choose Access Method

↓

Membership

OR

Buy Access

OR

PIN Code

↓

Authentication

↓

Payment (if required)

↓

Router Authorization

↓

Internet Access

---

# Modules

## Membership

Login

Forgot Password

Subscription Status

Hours Remaining

---

## Buy Access

Plans

Payment

Confirmation

Internet Access

---

## PIN

Validate Code

Activate Internet

Expiration Control

---

## Dashboard

Users

Memberships

Sales

PIN Codes

Reports

Analytics

Coupons

Promotions

---

# Coding Standards

Use semantic HTML.

Use reusable CSS classes.

Avoid duplicated code.

Keep JavaScript modular.

One responsibility per file.

Never mix business logic with UI.

---

# JavaScript Modules

app.js

Navigation

View changes

Global UI

login.js

Authentication

Validation

payment.js

Plans

Payments

Checkout

animations.js

Transitions

Hover effects

Micro animations

---

# Backend Architecture

Routers

↓

Services

↓

Repositories

↓

Database

Business logic must never exist inside routers.

---

# API Endpoints

POST /login

POST /purchase

POST /pin/validate

GET /plans

POST /membership

GET /dashboard

---

# Database Tables

Users

Memberships

Purchases

PIN Codes

Coupons

Payments

Sessions

---

# Long-Term Vision

The project should evolve from a captive portal into a complete management platform for:

Coffee Shops

Coworking Spaces

Hotels

Restaurants

Small Businesses

Including:

WiFi Management

Memberships

Payments

Reservations

Loyalty Programs

Promotions

Analytics

Reports

Admin Dashboard
