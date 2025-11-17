# Gmail SMTP Setup Guide

This guide will help you set up Gmail SMTP for sending password reset emails in the CENTEF RAG system.

## Overview

The system uses Gmail SMTP to send:
- Password reset emails
- Welcome emails for new users
- Other notifications (can be extended)

## Why Gmail SMTP?

- **Simple Setup**: Use your existing Gmail account
- **No API Keys**: Just need an App Password
- **Free**: Gmail allows sending emails at no cost
- **Reliable**: Gmail's infrastructure ensures delivery
- **No Daily Limits**: (for reasonable personal/internal use)

## Setup Steps

### 1. Enable 2-Factor Authentication (Required)

App Passwords only work if you have 2-Factor Authentication enabled on your Gmail account.

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Click on **2-Step Verification**
3. Follow the prompts to enable 2FA if not already enabled
4. You'll need your phone to receive verification codes

### 2. Generate an App Password

1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
   - Or: Google Account → Security → 2-Step Verification → App Passwords
2. You may need to sign in again
3. In the "Select app" dropdown, choose **Mail**
4. In the "Select device" dropdown, choose **Other (Custom name)**
5. Enter a name like: `CENTEF RAG Password Reset`
6. Click **Generate**
7. **IMPORTANT**: Copy the 16-character password immediately
   - It will look like: `abcd efgh ijkl mnop` (with spaces)
   - You can remove the spaces when copying: `abcdefghijklmnop`
   - You won't be able to see it again!

### 3. Update Your .env File

Add these variables to your `.env` file (or create it from `.env.example`):

```bash
# Email Configuration (Gmail SMTP)
GMAIL_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=abcdefghijklmnop
SENDER_NAME=CENTEF AI Platform
FRONTEND_URL=https://centef-rag-frontend-51695993895.us-central1.run.app
```

Replace:
- `your-email@gmail.com` with your actual Gmail address
- `abcdefghijklmnop` with the 16-character App Password (no spaces)
- Update `FRONTEND_URL` if different

### 4. Update Cloud Run Environment Variables

If deploying to Google Cloud Run, add the environment variables:

**Option A: Using gcloud command**
```bash
gcloud run services update centef-rag-api \
  --region us-central1 \
  --update-env-vars GMAIL_EMAIL=your-email@gmail.com,GMAIL_APP_PASSWORD=your-app-password,SENDER_NAME="CENTEF AI Platform",FRONTEND_URL=https://your-frontend-url.run.app
```

**Option B: Using deploy-backend-simple.ps1 (Recommended)**

The deployment script reads from your `.env` file automatically:
```powershell
powershell -ExecutionPolicy Bypass -File deploy-backend-simple.ps1
```

Make sure your `.env` file has the Gmail credentials before running the script.

## Testing the Integration

### Development Mode (Without Gmail Configured)

If Gmail credentials are not set, the system operates in development mode:
- Password reset emails are NOT sent
- The reset link is returned in the API response
- The link is also logged to console
- This allows testing without email configuration

### Production Mode (With Gmail SMTP)

Once Gmail is configured:
1. Request a password reset from the login page
2. Check your email inbox (and spam folder)
3. Click the reset link in the email
4. Reset your password
5. Login with the new password

## Email Templates

The system includes professionally designed email templates:
- Responsive design (mobile-friendly)
- Branded with CENTEF colors and styling
- Security warnings and expiration notices
- Plain text fallback for email clients that don't support HTML

### Password Reset Email Features:
- Clear call-to-action button
- 1-hour expiration notice
- Security warnings
- Plain text link as fallback
- Professional footer

## Troubleshooting

### Emails Not Arriving

1. **Check Spam Folder**: Gmail and other providers may filter automated emails
2. **Verify App Password**: Ensure the 16-character password is correct (no spaces)
3. **Check 2FA**: App Passwords require 2-Factor Authentication to be enabled
4. **Check Environment Variables**: Verify Gmail credentials are set in Cloud Run
5. **Check Logs**: Look at Cloud Run logs for error messages

### Common Issues

**"Username and Password not accepted"**
- Verify you're using an App Password, not your regular Gmail password
- Ensure 2-Factor Authentication is enabled
- Check that the App Password is entered correctly (no spaces)
- Try generating a new App Password

**"SMTP Authentication Error"**
- Verify GMAIL_EMAIL is your full Gmail address (e.g., user@gmail.com)
- Check that GMAIL_APP_PASSWORD has no spaces
- Ensure environment variables are set correctly

**Emails going to Spam**
- This is normal for automated emails from personal Gmail accounts
- Recipients may need to mark your emails as "Not Spam"
- For production, consider using a verified domain with SendGrid or similar service

### Getting Help

- Cloud Run logs: `gcloud run logs read centef-rag-api --region us-central1`
- Google Account Help: https://support.google.com/accounts
- App Passwords Help: https://support.google.com/accounts/answer/185833

## Security Best Practices

1. **Never commit App Passwords to git**
   - Keep them in `.env` file (which is git-ignored)
   - Use environment variables in production

2. **Use dedicated Gmail account (Optional)**
   - Consider creating a separate Gmail account for sending emails
   - Example: centef-notifications@gmail.com
   - This separates your personal email from system emails

3. **Rotate App Passwords periodically**
   - Revoke old App Passwords after creating new ones
   - Update Cloud Run environment variables when rotating

4. **Monitor sent emails**
   - Check Gmail's Sent folder periodically
   - Watch for unusual activity

## Limitations

### Gmail SMTP Limits
- **500 emails per day**: For regular Gmail accounts
- **2,000 emails per day**: For Google Workspace accounts
- Sufficient for:
  - Small to medium user base
  - Password resets
  - Welcome emails
  - Occasional notifications

### When to Upgrade to SendGrid or Similar

Consider switching to a dedicated email service if you need:
- More than 500 emails/day (for regular Gmail)
- Professional sender domain (not @gmail.com)
- Advanced features (A/B testing, analytics, etc.)
- Better deliverability guarantees
- Priority support

## Alternative: Using Google Workspace

If you have a Google Workspace account (formerly G Suite):
- Higher sending limits (2,000 emails/day)
- Use your professional domain (e.g., noreply@yourcompany.com)
- Same setup process with App Passwords
- Better professional appearance

## Next Steps

1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password
3. Update your `.env` file with Gmail credentials
4. Deploy backend with updated environment variables
5. Test password reset flow
6. Monitor email delivery

For production deployments with high email volume, refer to [SENDGRID_SETUP.md](SENDGRID_SETUP.md) for using SendGrid instead.
