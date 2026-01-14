# AWS Setup Guide for Textract

This guide will walk you through setting up AWS Textract access step by step.

## Step 1: Create AWS Account

1. Go to https://aws.amazon.com
2. Click "Create an AWS Account"
3. Follow the registration process (requires credit card)
4. Complete email verification

## Step 2: Sign in to AWS Console

1. Go to https://console.aws.amazon.com
2. Sign in with your account credentials
3. You should see the AWS Management Console

## Step 3: Create IAM User for Textract

### 3.1 Navigate to IAM
1. In the AWS Console, search for "IAM" in the search bar
2. Click on "IAM" service

### 3.2 Create User
1. Click "Users" in the left sidebar
2. Click "Create user" button
3. Enter username: `textract-user` (or any name you prefer)
4. Click "Next"

### 3.3 Set Permissions
1. Select "Attach policies directly"
2. In the search box, type "textract"
3. Check the box next to "AmazonTextractFullAccess"
4. Click "Next"

### 3.4 Review and Create
1. Review the user details
2. Click "Create user"
3. You should see "User created successfully"

## Step 4: Generate Access Keys

### 4.1 Access User Settings
1. Click on the username you just created (`textract-user`)
2. Click on the "Security credentials" tab

### 4.2 Create Access Key
1. Scroll down to "Access keys" section
2. Click "Create access key"
3. Select "Application running outside AWS"
4. Click "Next"

### 4.3 Optional Description
1. Add description (optional): "Document processing tool"
2. Click "Create access key"

### 4.4 Save Your Keys
**IMPORTANT**: This is the only time you'll see the secret key!

1. Copy the "Access key ID" - it looks like: `AKIAIOSFODNN7EXAMPLE`
2. Copy the "Secret access key" - it looks like: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`
3. Click "Done"

## Step 5: Configure Your Project

### 5.1 Create .env File
In your project directory, create a `.env` file:

```env
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
```

Replace the example values with your actual keys from Step 4.4.

### 5.2 Test Your Setup
Run the test script:

```bash
python test_setup.py
```

You should see:
```
✅ All modules imported successfully
✅ AWS credentials found (Region: us-east-1)
✅ Textract client initialized successfully
🎉 All tests passed! You're ready to process documents.
```

## Step 6: Verify Textract Access

### 6.1 Check Service Availability
1. In AWS Console, search for "Textract"
2. Click on "Amazon Textract"
3. Make sure it's available in your region (us-east-1 recommended)

### 6.2 Test with Sample Document
```bash
# Place any PDF or image in your project directory
python -m src.cli sample_document.pdf
```

## Troubleshooting

### Error: "AWS credentials not found"
- Check your `.env` file exists and has the correct format
- Ensure no extra spaces around the `=` signs
- Verify the keys are copied correctly

### Error: "AccessDeniedException"
- Your IAM user doesn't have Textract permissions
- Go back to IAM → Users → your user → Permissions
- Ensure "AmazonTextractFullAccess" policy is attached

### Error: "InvalidParameterException"
- Your file might be too large (>10MB) or unsupported format
- Try with a smaller PDF or PNG/JPG image

### Error: "Region not supported"
- Textract is not available in all regions
- Change AWS_REGION to `us-east-1` or `us-west-2`

## AWS Costs

### Textract Pricing (as of 2024)
- **AnalyzeDocument API**: ~$1.50 per 1,000 pages
- **Free Tier**: 1,000 pages per month for first 3 months (new accounts)

### Cost Examples
- 10 invoices (1 page each): ~$0.015
- 100 invoices: ~$0.15
- 1,000 invoices: ~$1.50

### Monitor Costs
1. AWS Console → Billing Dashboard
2. Set up billing alerts if needed

## Security Best Practices

### 1. Limit Permissions
- Only use AmazonTextractFullAccess (don't use admin access)
- Consider creating custom policy with minimal permissions

### 2. Rotate Keys Regularly
- Generate new access keys every 90 days
- Delete old keys after updating your `.env` file

### 3. Keep Keys Secret
- Never commit `.env` file to version control
- Don't share keys in chat/email
- Use environment variables in production

### 4. Monitor Usage
- Check AWS CloudTrail for API calls
- Set up billing alerts for unexpected charges

## Alternative: AWS CLI Configuration

Instead of `.env` file, you can use AWS CLI:

```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure
# Enter your Access Key ID
# Enter your Secret Access Key  
# Enter region: us-east-1
# Enter output format: json
```

The tool will automatically use these credentials.

## Next Steps

Once setup is complete:

1. **Test with sample documents**: Try different PDF and image formats
2. **Check output quality**: Review extracted text accuracy
3. **Integrate into workflow**: Use the Python API in your applications
4. **Monitor costs**: Keep track of Textract usage

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Verify your AWS account is active and verified
3. Ensure billing information is up to date
4. Try with different document formats/sizes

## Summary Checklist

- [ ] AWS account created and verified
- [ ] IAM user created with Textract permissions
- [ ] Access keys generated and saved
- [ ] `.env` file created with credentials
- [ ] Test script passes all checks
- [ ] Sample document processed successfully

You're now ready to extract text from documents using AWS Textract!