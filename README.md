# Discord bot for ERLC private server- Don't claim as yours! :)

A custom Discord bot originally developed for the **Las Vegas Roleplay (LVRP)** server.  
This project demonstrates my ability to build, maintain, and scale Discord bots with advanced features for server management, automation, and community engagement.

Note: Not all functions were added to the bot nor all functions were tested, avoid using this script unless you know how to code. You have to modify if you want to use it for your own server.
---
Contact me at discord: marty_fabio_
---

## 📌 Features
- **Moderation tools**  
  Remove role or add role, promote or infract your staff.

- **Staff management**  
  Add/remove roles, promote/demote, review system for tracking performance.

- **Utility commands**  
  Custom announcements, tickets, and role management.

- **Database integration**  
  Uses SQLite/JSON for persistent storage (e.g., appeals, staff reviews, user data).

- **Modular design (Cogs)**  
  Easy to extend and maintain with separate modules for each feature.

---

## 🛠️ Tech Stack
- **Language**: Python 3  
- **Library**: discord.py and many more.
- **Database**: SQLite  
- **Hosting**: Local testing + production-ready deployment but require some editings in code so it work for your server, contact @marty_fabio_ on discord to get a production ready bot!

---

## ⚙️ Main Commands
### Staff & Role Management
- `/add_role` – Assign a role to a member  
- `/remove_role` – Remove a role from a member  
- `/promote` – Promote staff members  

### Moderation & Infractions
- `/infract` – Add an infraction to a user  

### Staff Review System
- `/review staff` – Submit a review for a staff member  
- `/myreview` – View your submitted reviews  
- `/remove staff review` – Delete a review entry  
- `/view staff reviews` – View all reviews of a staff member  




