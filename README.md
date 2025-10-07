# Discord Bot for ERLC Private Server  
⚠️ **Do not claim this project as your own!** ⚠️  
 
This project demonstrates my ability to build, maintain, and scale Discord bots with advanced features for server management, automation, and community engagement.  

> **Note**: Not all functions were added or fully tested. Avoid using this script unless you know how to code.  
> You will need to **modify the code** to make it work for your own server.  

📩 Contact: **Discord – `marty_fabio_`**  

---

## 📌 Features
- **Moderation Tools** – Add/remove roles, promote, and infract staff.  
- **Staff Management** – Complete system for promotions, demotions, and performance reviews.  
- **Utility Commands** – Custom announcements, tickets, and role management.  
- **Database Integration** – SQLite/JSON for storing appeals, staff reviews, and user data.  
- **Modular Design (Cogs)** – Clean, scalable code organization.  
- **Security & Anti-Spam** – Permission checks and basic anti-spam for fun commands.  

---

## 🛠️ Tech Stack
- **Language**: Python 3  
- **Library**: discord.py
- **Database**: SQLite / JSON  
- **Hosting**: Local testing + production-ready deployment (requires edits for your server).  
  > For a production-ready bot, contact me at **`marty_fabio_`**.  

---

## ⚙️ Main Commands

### 🔹 Staff & Role Management
- `/add_role` – Assign a role to a member  
- `/remove_role` – Remove a role from a member  
- `/promote` – Promote a staff member  

### 🔹 Moderation & Infractions
- `/infract` – Add an infraction to a user  
- **Ban Appeals System** – Bot posts an embed in a channel; members click "Submit" to fill out a form.  
  - Appeals are sent to a review channel.  
  - HR can **accept** or **deny** directly.  

### 🔹 Staff Review System
- `/review staff` – Submit a review for a staff member  
- `/myreview` – View your submitted reviews  
- `/remove staff review` – Delete a review entry  
- `/view staff reviews` – View all reviews of a staff member  

---

## 🎉 Fun Commands
- `!joke` – Sends a random joke in the channel  
- `!joke @mention` – Pings the mentioned user with a joke  
- `!yesno question` – Randomly replies with "Yes," "No," "Certainly," or a negative response  

---

## ⚠️ Disclaimer
This bot was designed with **security in mind**:  
- Permission checks are in place before command execution.  
- Anti-spam protection for fun commands.  
- Not all features are finalized – expect bugs if you use it without modifications.  






