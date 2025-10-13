# Payment System Guide

## Overview

The VulnEats food ordering system uses **Chapa** as the payment gateway for processing payments. This guide explains how the payment system works and how to use the new webhook functionality.

## Payment Flow

### 1. Order Placement
When a user places an order:
1. System creates a payment record in the `payments` table with status `'initialized'`
2. Generates a unique transaction reference (`tx_ref`)
3. Redirects user to Chapa payment page

### 2. Payment Processing
- User completes payment on Chapa's platform
- Chapa processes the payment
- Chapa sends webhook notification to our system

### 3. Payment Verification
- Our webhook endpoint receives the payment status
- Verifies the payment with Chapa's API
- Updates the payment status in the database
- User is redirected back to the dashboard

## Database Schema

### Payments Table
```sql
CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    provider TEXT NOT NULL,
    tx_ref TEXT UNIQUE NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Payment Statuses
- `'initialized'` - Payment created, waiting for user action
- `'paid'` - Payment successful
- `'failed'` - Payment failed

## API Endpoints

### 1. Payment Checkout
**POST** `/api/payments/chapa/checkout`
- Creates a new payment and redirects to Chapa
- Body: `{"restaurant_id": 123}`

### 2. Batch Payment Checkout
**POST** `/api/payments/chapa/checkout/batch`
- Creates multiple payments for different restaurants
- Used when user has items from multiple restaurants

### 3. Payment Verification (GET)
**GET** `/api/payments/chapa/verify?tx_ref={tx_ref}`
- Manually verify payment status
- Used by frontend after user returns from payment

### 4. Webhook Endpoint (NEW)
**POST** `/api/payments/chapa/webhook`
- Receives automatic payment notifications from Chapa
- Verifies payment status and updates database
- Includes signature verification for security

### 5. Payment Status Check
**GET** `/api/payments/status/{tx_ref}`
- Get detailed payment information
- Requires user authentication
- Returns payment details and order information

### 6. Webhook Health Check
**GET** `/api/payments/webhook/status`
- Check if webhook is properly configured
- Useful for monitoring and debugging

## Webhook Implementation

### Security Features
1. **Signature Verification**: Verifies webhook authenticity using HMAC-SHA256
2. **API Verification**: Double-checks payment status with Chapa API
3. **Error Handling**: Comprehensive error handling and logging
4. **Rate Limiting**: Built-in protection against spam

### Webhook Payload Example
```json
{
    "tx_ref": "vulneats-abc123",
    "status": "success",
    "message": "Payment completed successfully",
    "data": {
        "status": "success",
        "amount": "100.00",
        "currency": "ETB"
    }
}
```

### Webhook Headers
- `Content-Type: application/json`
- `X-Chapa-Signature: <hmac_signature>` (optional)

## Configuration

### Environment Variables
```bash
CHAPA_SECRET_KEY=your_chapa_secret_key
BACKEND_BASE_URL=https://your-backend.com
FRONTEND_BASE_URL=https://your-frontend.com
```

### Chapa Configuration
In your Chapa dashboard, set the webhook URL to:
```
https://your-backend.com/api/payments/chapa/webhook
```

## Testing

### Manual Testing
Use the provided test script:
```bash
python test_webhook.py
```

### Test Cases
1. ✅ Valid webhook with signature
2. ✅ Valid webhook without signature
3. ❌ Invalid JSON payload
4. ❌ Missing tx_ref
5. ❌ Invalid signature

## Frontend Integration

### Dashboard Integration
The dashboard automatically:
1. Detects `tx_ref` in URL parameters
2. Verifies payment status
3. Shows payment confirmation
4. Cleans up URL parameters

### Payment Status Display
```typescript
// Example payment status check
const checkPaymentStatus = async (txRef: string) => {
  const response = await fetch(`/api/payments/status/${txRef}`, {
    credentials: 'include'
  });
  const data = await response.json();
  
  if (data.ok && data.payment) {
    console.log(`Payment status: ${data.payment.status}`);
  }
};
```

## Error Handling

### Common Error Codes
- `400` - Invalid payload or missing tx_ref
- `403` - Invalid signature or unauthorized access
- `404` - Payment not found
- `500` - Internal server error
- `502` - Chapa API verification failed
- `503` - Payment service unavailable

### Logging
All webhook events are logged with:
- Transaction reference
- Payment status changes
- Error details
- Timestamps

## Security Best Practices

1. **Always verify webhook signatures** when available
2. **Use HTTPS** for all webhook endpoints
3. **Validate all input data** from webhooks
4. **Implement rate limiting** to prevent abuse
5. **Log all webhook events** for monitoring
6. **Use environment variables** for sensitive data

## Troubleshooting

### Webhook Not Receiving Calls
1. Check Chapa dashboard webhook configuration
2. Verify webhook URL is accessible
3. Check server logs for errors
4. Test webhook endpoint manually

### Payment Status Not Updating
1. Check database connection
2. Verify payments table exists
3. Check Chapa API credentials
4. Review webhook logs

### Signature Verification Failing
1. Verify CHAPA_SECRET_KEY is correct
2. Check signature algorithm matches Chapa's
3. Ensure raw request body is used for verification

## Future Enhancements

1. **Webhook Retry Logic**: Implement automatic retry for failed webhooks
2. **Payment Analytics**: Add payment success/failure metrics
3. **Multi-Currency Support**: Support for different currencies
4. **Payment Methods**: Add support for other payment providers
5. **Real-time Notifications**: WebSocket notifications for payment updates

## Support

For issues with the payment system:
1. Check server logs
2. Verify Chapa configuration
3. Test webhook endpoints
4. Review this documentation
