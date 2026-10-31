# SK Soft Technology IT Support Guide

## New joiner laptop setup (software to install)
Your laptop comes with Windows/macOS, the antivirus and the Software Center already installed. On day 1:
1. Sign in with your SK Soft email and set up multi-factor authentication (MFA) with the Microsoft Authenticator app on your phone.
2. Install the SK Soft VPN client from the Software Center and connect once to check it works.
3. From the Software Center install the standard tools: Microsoft Outlook and Teams, Slack, Google Chrome, 7-Zip and Zoom.
4. Developers also install, from the Software Center: Git, Visual Studio Code (or IntelliJ IDEA), Docker Desktop, Postman, and Python or Node.js as your project needs.
5. Raise an Access Request in the IT Service Portal for GitHub, Jira, Confluence and the AWS dev account (see below).
6. Do not install personal or pirated software; anything not in the Software Center needs an IT request.
- IT runs a 30-minute "Laptop Ready" session for new joiners every Monday at 11 AM on Teams.

## Access to GitHub, Jira, Confluence and AWS
1. Raise an Access Request in the IT Service Portal and select the tools you need (GitHub organisation, Jira project, Confluence space, AWS dev account).
2. Mention the project code and your project manager's name.
3. Your project manager approves the request in the portal.
4. Standard access is provided within 1 working day after approval.
- Production (AWS prod, production databases) access needs extra approval from the delivery head and is given only for a limited time.
- Access is removed automatically when you are released from a project.

## VPN not connecting or disconnecting
1. Make sure you have the latest SK Soft VPN client (updates are pushed every month).
2. Restart the VPN client and sign in again with multi-factor authentication (MFA).
3. Switch to another network (for example a mobile hotspot) to check whether your home Wi-Fi is the problem.
4. If it still drops, raise an IT ticket with a screenshot of the error and the time it happened.

## Reset your office password
1. Go to the Self-Service Password Portal and enter your employee ID.
2. Verify with the code sent to your registered mobile or the authenticator app.
3. Choose a password with at least 12 characters, including upper case, lower case, a number and a symbol.
4. Passwords expire every 90 days and the last 5 cannot be reused.

## Laptops and software
- Developer laptops have 32 GB RAM and are replaced every 4 years.
- Hardware faults are fixed within 3 working days; a spare laptop is given if it takes longer.
- Install licensed software (IDEs, Docker Desktop, database tools) only from the Software Center or by raising a request. Pirated or personal-licence software is not allowed.

## Security incidents
- Report a lost or stolen laptop to IT and your manager within 2 hours so it can be locked and wiped remotely.
- Never share passwords or MFA codes, even with IT staff.
- Report phishing emails with the Report Phishing button in Outlook.
- Never commit secrets, passwords or API keys to GitHub; if it happens, inform the security team immediately so the key is rotated.
