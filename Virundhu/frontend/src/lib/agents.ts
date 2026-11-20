/**
 * The one list of agent names used everywhere: website, restaurant app, admin, emails, catalog.
 * Backend copies: services/ai_staff.py (restaurant staff) and services/agent_team.py TEAM (service agents).
 * Change a name here and there together.
 */

/** "Your AI staff": work for each restaurant. */
export const RESTAURANT_STAFF = [
  { name: "Kavya", role: "The Guest Whisperer", job: "Reads every review the moment it lands, in Tamil, Tanglish or English." },
  { name: "Arjun", role: "The Reply Maestro", job: "Writes the reply in the guest's language; posts happy Google replies by himself." },
  { name: "Meera", role: "The Kitchen Guardian", job: "Food-safety and hygiene complaints reach your branch manager within a minute." },
  { name: "Vikram", role: "The Trouble Spotter", job: "Spots the same complaint repeating at one outlet before it hurts your rating." },
  { name: "Anbu", role: "The Comeback Captain", job: "Sends unhappy guests an apology and a comeback code, then tells you who returned." },
  { name: "Malar", role: "The Star Builder", job: "Invites happy guests to post on Google, so your rating climbs." },
  { name: "Siva", role: "The Monday Strategist", job: "Monday brief: what to fix, which dish, who to thank, how each outlet moved." },
] as const;

/** Virundhu's own team: they run the service for every restaurant. */
export const SERVICE_AGENTS = [
  { name: "Mani", role: "The Operations Lead", job: "Hands every job to the right agent, every minute, day and night." },
  { name: "Nila", role: "The Demo Booker", job: "Emails open demo times; one tap books it, with a calendar invite and reminders." },
  { name: "Tara", role: "The Help Desk Hero", job: "Answers support tickets in minutes and fixes payment problems by herself." },
  { name: "Isai", role: "The Feedback Listener", job: "Reads every idea and complaint about Virundhu and sends it where it helps." },
  { name: "Ravi", role: "The Trial Saver", job: "Reminds you before your trial ends and unlocks your account the moment you pay." },
  { name: "Lakshmi", role: "The Money Keeper", job: "Switches your plan on when you pay and emails your receipt." },
  { name: "Dev", role: "The Night Watch", job: "Backs up your data every night and checks that every sync and email worked." },
] as const;
