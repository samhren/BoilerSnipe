# Transparency Statement

This document describes exactly what BoilerSnipe accesses, how often, and how to contact us.
It exists so that Purdue University staff, or anyone else, can understand what this tool does
without having to read the source code or infer it from traffic logs.

A user-facing version of this page lives at [boilersnipe.com/about](https://boilersnipe.com/about).

## What BoilerSnipe is

BoilerSnipe is a free tool built by a Purdue student.
It watches Purdue course sections that a student has asked it to watch, and emails that student when a section goes from full to having an open seat.

It is free to use, it is not a business, and there are no plans to charge for it or to sell anything.

## What data we access

We read publicly available course pages from Purdue's self-service scheduling system at `selfservice.mypurdue.purdue.edu`.
These pages are served to anyone on the internet without logging in.

From those pages we read only:

- The course listing: CRN, course code, title, instructor, meeting time, section
- The "Registration Availability" table: seat capacity, seats taken, seats remaining

We do not read, store, or transmit any personal information about any student from Purdue's systems, because none is present on the pages we read.

## How often we request pages

- **Seat checks** run on a fixed interval, currently every 5 minutes, and only for course sections that at least one signed-in user is actively tracking.
  We do not poll the full catalog for seat counts.
  See `backend/workers/sniper.py` and the `SNIPER_INTERVAL_MINUTES` setting.
- **Course listings** for the current term are collected when the background worker starts, and optionally on a weekly schedule, to keep search results current.
  See `backend/workers/inventory_scraper.py` and the `INVENTORY_CRON` setting.

## How to identify our traffic

Our requests identify themselves rather than imitating a web browser.
They are sent with this user agent:

```
BoilerSnipe/1.0 (+https://boilersnipe.com/about; contact@boilersnipe.com)
```

This is set in one place, `USER_AGENT` in `backend/app/config.py`, and is used by both the seat checker and the inventory scraper.

## What we never do

- We never ask for, store, or use a student's Purdue credentials or Career Account.
- We never log in to myPurdue or any authenticated Purdue system.
- We never register, drop, or hold a seat for anyone.
  BoilerSnipe only sends a notification.
  Registering is something the student does themselves, through Purdue's own system.
- We never access data that is not already public.
- We never sell user data or share it with advertisers.

## Relationship to Purdue University

BoilerSnipe is not affiliated with, endorsed by, sponsored by, or connected to Purdue University in any way.
"Purdue," "Boilermaker," and related names and logos are trademarks of their respective owners.
We use the name "Purdue" only to describe which university's course data the tool covers.

## For Purdue faculty, staff, and IT

If you work for Purdue and have any concern about this tool, please contact us at **contact@boilersnipe.com**.
We will respond quickly.

**If Purdue asks us to reduce our request rate, change how the tool works, or shut it down entirely, we will comply immediately and without argument.**
We would rather be asked than blocked.

If Purdue has an official course data feed or API we should be using instead of reading public pages, we would much prefer to use it.
Please tell us and we will migrate.
