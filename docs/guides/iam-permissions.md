# IAM permissions

AWS IAM policies your service needs to use pydynox features.

## Key features

- Minimal permissions for each feature
- Copy-paste ready policies
- Separate policies for DynamoDB and KMS

## DynamoDB permissions

### Basic CRUD

For read and write operations:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/TABLE_NAME"
        }
    ]
}
```

### Batch operations

Add these for batch read/write:

```json
{
    "Effect": "Allow",
    "Action": [
        "dynamodb:BatchGetItem",
        "dynamodb:BatchWriteItem"
    ],
    "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/TABLE_NAME"
}
```

### Transactions

Add these for transactional operations:

```json
{
    "Effect": "Allow",
    "Action": [
        "dynamodb:TransactGetItems",
        "dynamodb:TransactWriteItems"
    ],
    "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/TABLE_NAME"
}
```

### Table management

For creating and managing tables:

```json
{
    "Effect": "Allow",
    "Action": [
        "dynamodb:CreateTable",
        "dynamodb:DeleteTable",
        "dynamodb:DescribeTable",
        "dynamodb:UpdateTable"
    ],
    "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/TABLE_NAME"
}
```

## KMS permissions (for encryption)

pydynox uses envelope encryption with `kms:GenerateDataKey` instead of `kms:Encrypt`. This removes the 4KB size limit and reduces KMS API calls.

### Full access (ReadWrite mode)

For services that encrypt and decrypt:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "kms:GenerateDataKey",
                "kms:Decrypt"
            ],
            "Resource": "arn:aws:kms:REGION:ACCOUNT:key/KEY_ID"
        }
    ]
}
```

### Write-only (WriteOnly mode)

For services that only write encrypted data:

```json
{
    "Effect": "Allow",
    "Action": [
        "kms:GenerateDataKey"
    ],
    "Resource": "arn:aws:kms:REGION:ACCOUNT:key/KEY_ID"
}
```

### Read-only (ReadOnly mode)

For services that only read encrypted data:

```json
{
    "Effect": "Allow",
    "Action": [
        "kms:Decrypt"
    ],
    "Resource": "arn:aws:kms:REGION:ACCOUNT:key/KEY_ID"
}
```

## Complete example

A service that does CRUD, batch operations, and field encryption:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DynamoDBAccess",
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:BatchGetItem",
                "dynamodb:BatchWriteItem"
            ],
            "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/users"
        },
        {
            "Sid": "KMSAccess",
            "Effect": "Allow",
            "Action": [
                "kms:GenerateDataKey",
                "kms:Decrypt"
            ],
            "Resource": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
        }
    ]
}
```

## Tips

- **Use least privilege** - Only grant the permissions your service needs
- **Use resource ARNs** - Don't use `*` for resources
- **Separate read and write** - Use different roles for read-only and write services
- **Use KMS key aliases** - Easier to manage than key IDs in policies
- **Test permissions** - Use IAM Policy Simulator to verify your policies


## Next steps

- [Client](client.md) - Configure the DynamoDB client
- [Encryption](encryption.md) - KMS permissions for encryption
- [Tables](tables.md) - Table management permissions
