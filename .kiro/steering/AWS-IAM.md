---
inclusion: always
---


# AWS IAM Policies
When writing any code on AWS permissions or policies, you should follow the following requirements: 

## Key categories to define
Always define the following categories: Users, Roles, Policies, AWS Accounts, conditions

### 1. Users:
    - Is it a human user or a system user
    - You MUST design the system so it is EITHER a human or a system, it MUST NOT be both

### 2. Roles:
    - What role(s) does the user require?
    - Humans will be provisioned with a permission set in AWS Identity Centre
    - Systems will be provisioned with an AWS IAM Role

### 3. Policies:
    - What permissions does the user require to complete their task? 
    - All policies MUST be least privileged and MUST NOT include permissions which are not used when executing the code that the actor will run

### AWS Accounts
    - Which AWS account should this permission be granted in? 
    - Are cross account permissions required? If so, from which account to which account?

### Conditions
    - What conditions can be added to increase the security of the configuration?
    - Add reasonable condition keys


## How to document the AWS IAM configuration

### Structure and location
    - All policies and roles MUST be written in cloudformation
    - All cloudformation must reside within a directory at the project root named /cloudformation/

### How to write policies
    - All policies MUST be written as valid AWS IAM Policy Cloudformation files
    - You MUST write all policies/roles as a Cloudformation file
    - You MUST NOT use a '''cat >> some-policy.json <<EOF etc etc EOF''' format in documentation
    - You MUST create all policy files for the user, DO NOT ask the user to create a policy file

### Provide user guidance
- If any code should be executed by a user, you MUST provide clear instructions in the documentation that explain:
    - What permissions the user will require and which policy those permissions are contained in
    - Link to the policy document in the repository structure
    - Describe how an administrator should deploy the role/policy to an AWS account using cloudformation (include instructions on WHICH account)
