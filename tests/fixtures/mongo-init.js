db = db.getSiblingDB("testing");  // Create/use database

db.auth_projects.insertMany([
    {
      "_id":  ObjectId("67bdc0641ac599506aa6ec7e"),
      "ext_id": "project-test",
      "name": "test project",
      "version": 2,
      "admin_id": "67bdbfd8b790ddf03785119e",
      "admin_email": null,
      "user_emails": null,
      "user_ids": [
        "67bdbfd8b790ddf03785119e"
      ],
      "qpu_seconds": 9000000,
      "source": "internal",
      "resource_ids": [],
      "description": "Some project",
      "is_active": true,
      "created_at": "2024-11-05T15:13:49.368Z",
      "updated_at": "2024-12-16T11:20:33.848Z"
    }
]);

db.auth_app_tokens.insertMany([
    {
      "_id": ObjectId("67bdc2aacd991c8e1cf16ffc"),
      "title": "some-token-test",
      "project_ext_id": "project-test",
      "lifespan_seconds": 7200000,
      "token": "pZTccp8F-8RLFvQie1AMM0ptfdkGNnH1wDEB4INUFqw",
      "user_id": ObjectId("67bdbfd8b790ddf03785119e"),
      "created_at": ISODate()
    }
])

db.auth_users.insertMany(
[
    {
      "_id": ObjectId("67bdbfd8b790ddf03785119e"),
      "email": "jane.doe@example.com",
      "hashed_password": "hashed_password",
      "is_active": true,
      "is_verified": true,
      "oauth_accounts": [
      ],
      "roles": [
        "system",
        "admin",
        "user"
      ]
    }
]
)