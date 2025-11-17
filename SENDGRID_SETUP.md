# SendGrid Email Setup Guide

This guide will help you set up SendGrid for sending password reset emails in the CENTEF RAG system.

## Overview

The system uses SendGrid to send:
- Password reset emails
- Welcome emails for new users
- Other notifications (can be extended)

## Free Tier

SendGrid offers a generous free tier:
- **100 emails per day** - Perfect for most applications
- No credit card required for signup
- All features included

## Setup Steps

### 1. Create a SendGrid Account

1. Go to [https://sendgrid.com/](https://sendgrid.com/)
2. Click "Start for free" or "Sign Up"
3. Fill in your information:
   - Email address
   - Password
   - Company name (can use "CENTEF" or your organization)
4. Verify your email address

### 2. Create an API Key

1. Log in to your SendGrid dashboard
2. Navigate to **Settings** → **API Keys**
3. Click "Create API Key"
4. Configure the key:
   - **Name**: `CENTEF-RAG-Password-Reset`
   - **API Key Permissions**: Select "Restricted Access"
   - Enable only: **Mail Send** → **Mail Send** (Full Access)
5. Click "Create & View"
6. **IMPORTANT**: Copy the API key immediately - you won't be able to see it again!
   - It should start with `SG.`
   - Example: `SG.abc123...`

### 3. Verify Sender Identity

SendGrid requires you to verify your sender email address or domain.

#### Option A: Single Sender Verification (Quick & Easy)

1. Go to **Settings** → **Sender Authentication**
2. Click "Verify a Single Sender"
3. Fill in the form:
   - **From Name**: CENTEF AI Platform
   - **From Email Address**: noreply@yourdomain.com (use your actual domain)
   - **Reply To**: support@yourdomain.com (optional)
   - **Company Address**: Your organization's address
4. Click "Create"
5. Check your email and click the verification link

#### Option B: Domain Authentication (Recommended for Production)

1. Go to **Settings** → **Sender Authentication**
2. Click "Authenticate Your Domain"
3. Follow the DNS setup instructions for your domain
4. This provides better deliverability and professional appearance

### 4. Update Environment Variables

Add these variables to your `.env` file:

```bash
# SendGrid Email Configuration
SENDGRID_API_KEY=SG.your-actual-api-key-here
SENDER_EMAIL=noreply@yourdomain.com
SENDER_NAME=CENTEF AI Platform
FRONTEND_URL=https://your-frontend-url.run.app
```

### 5. Update Cloud Run Environment Variables

If deploying to Google Cloud Run, add the environment variables:

```bash
gcloud run services update centef-rag-api \
  --region us-central1 \
  --update-env-vars SENDGRID_API_KEY=SG.your-key-here,SENDER_EMAIL=noreply@yourdomain.com,SENDER_NAME="CENTEF AI Platform",FRONTEND_URL=https://your-frontend-url.run.app
```

Or use the `deploy-backend-simple.ps1` script which reads from `.env` file.

## Testing the Integration

### Development Mode (Without SendGrid)

If `SENDGRID_API_KEY` is not set, the system operates in development mode:
- Password reset emails are NOT sent
- The reset link is returned in the API response
- The link is also logged to console
- This allows testing without email configuration

### Production Mode (With SendGrid)

Once SendGrid is configured:
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

### Welcome Email Features (for future use):
- Welcoming message
- Login credentials (if applicable)
- Direct login link
- Getting started information

## Customization

### Changing Email Appearance

Edit `shared/email_service.py` to customize:
- Colors and styling
- Email content and wording
- Sender information
- Email templates

### Adding New Email Types

The `email_service.py` module is designed to be extended:

```python
def send_custom_notification(to_email: str, ...):
    # Add your custom email logic here
    pass
```

## Troubleshooting

### Emails Not Arriving

1. **Check Spam Folder**: Gmail and other providers may filter automated emails
2. **Verify Sender**: Ensure your sender email is verified in SendGrid
3. **Check API Key**: Verify the API key has "Mail Send" permissions
4. **Check Logs**: Look at Cloud Run logs for error messages
5. **SendGrid Activity**: Check SendGrid dashboard → Activity for delivery status

### Common Issues

**"Invalid API Key"**
- Verify the API key starts with `SG.`
- Ensure no extra spaces in the environment variable
- Check that the API key hasn't been deleted

**"Sender email not verified"**
- Complete single sender verification
- Or set up domain authentication

**"Rate limit exceeded"**
- Free tier is limited to 100 emails/day
- Upgrade plan if needed

### Getting Help

- SendGrid Documentation: https://docs.sendgrid.com/
- SendGrid Support: https://support.sendgrid.com/
- Check backend logs: `gcloud run logs read centef-rag-api --region us-central1`

## Security Best Practices

1. **Never commit API keys to git**
   - Keep them in `.env` file (which is git-ignored)
   - Use environment variables in production

2. **Use restricted API keys**
   - Only grant "Mail Send" permission
   - Don't use Full Access keys

3. **Rotate keys periodically**
   - Create new keys every 90 days
   - Delete old keys after rotation

4. **Monitor usage**
   - Check SendGrid dashboard regularly
   - Set up alerts for unusual activity

## Cost Considerations

### Free Tier Limits
- 100 emails/day (3,000/month)
- Sufficient for:
  - Small to medium user base
  - Password resets
  - Welcome emails
  - Occasional notifications

### When to Upgrade
Consider upgrading if you need:
- More than 100 emails/day
- Dedicated IP address
- Advanced features (A/B testing, etc.)
- Priority support

### Pricing
- Free: $0/month (100 emails/day)
- Essentials: $19.95/month (50,000 emails/month)
- Pro: Custom pricing for higher volumes

## Next Steps

1. Set up your SendGrid account
2. Create and configure your API key
3. Verify your sender email
4. Update environment variables
5. Test password reset flow
6. Monitor email delivery

For additional features or customization, refer to the SendGrid API documentation.
