# Team Email Invite Design

## Goal

Add a real team membership flow so the Team page can invite platform users by email and show the current roster from backend data instead of static mock members.

This feature is intentionally lightweight:

- Invite by email only
- Treat existing Eko users as immediate members
- Treat unknown emails as pending invites
- Keep the current single-workspace assumption
- Avoid email delivery, confirmation emails, and org hierarchy for now

## Scope

In scope:

- A persistent team member store in the backend
- A backend API to list team members
- A backend API to invite a member by email
- A backend API to remove a member
- A frontend team page that renders the live member list
- A frontend invite form/modal on the Team page

Out of scope:

- Sending real invite emails
- Accept/decline invite flows
- Multi-team or nested organization structures
- Role management beyond the minimal owner/member split
- Cross-workspace membership

## Product Behavior

The Team page should show:

- The current user and their role
- Existing members already joined to the team
- Pending invite rows for emails not yet registered as Eko accounts

Inviting a person works like this:

1. User enters an email address
2. Frontend submits it to the backend
3. Backend looks up an Eko user by that email
4. If a user exists, the person becomes an active team member immediately
5. If no user exists, the backend stores a pending invite record
6. The Team page refreshes and reflects the latest status

Duplicate invitations should not create duplicate visible members. Re-inviting the same email should update the existing record or return the existing pending row.

## Backend Design

### Data Model

Add a new team domain with two core entities:

- `Team`
  - Represents the current workspace team
  - For this project, one default team is enough

- `TeamMember`
  - Stores membership state for a user or invited email
  - Fields:
    - `id`
    - `team_id`
    - `user_id` nullable
    - `email`
    - `display_name` nullable
    - `role` (`owner` or `member`)
    - `status` (`active` or `invited`)
    - `invited_by_user_id` nullable
    - `created_at`
    - `updated_at`

Membership rules:

- An active user member has both `user_id` and `email`
- A pending invite has `email` and no `user_id`
- The owner is seeded from the current logged-in user on first access if the team has no members yet
- Only one row per email per team should exist

### API

Add a team router with these endpoints:

- `GET /api/v1/team/members`
  - Returns the current roster
  - Includes active members and pending invites

- `POST /api/v1/team/members/invite`
  - Body: `{ "email": "person@example.com" }`
  - If the email matches an existing Eko user, create or activate membership
  - Otherwise create or update a pending invite row

- `DELETE /api/v1/team/members/{member_id}`
  - Removes the member or invite row
  - The current owner cannot be removed

Response shape should be frontend-friendly and explicit about status:

- `id`
- `email`
- `display_name`
- `role`
- `status`
- `avatar_url`
- `is_current_user`
- `is_registered_user`
- `invited_by_name`
- `created_at`

### Integration With Auth

The existing authenticated user is already available through the auth/session layer. The team flow should reuse that user identity rather than creating a separate concept of team login.

The backend should use the current user as:

- the default owner seed for an empty team
- the inviter for new invites

### Persistence

The app currently creates database tables on startup using SQLAlchemy metadata. The new team models should be imported into the metadata bootstrap path so tables are created automatically in development.

## Frontend Design

The Team page should stop using hard-coded member cards and render data fetched from the backend.

UI structure:

- Header with team name and member count
- Primary action button: `邀请成员`
- Member list card/grid with:
  - avatar or initials
  - name or email fallback
  - role badge
  - status badge for pending invites
  - optional remove action for non-owner members

Invite flow:

- Clicking `邀请成员` opens a small form
- The form accepts one email address
- On submit, show loading state
- On success, close the form and refresh the list
- On validation error, show inline feedback

The initial implementation should keep the page visually aligned with the existing workspace UI. No redesign is needed.

## Error Handling

Expected error cases:

- Invalid email format
- Duplicate invite or duplicate membership
- Attempting to remove the owner
- Unauthenticated access

Behavior:

- Invalid email shows inline form error
- Duplicate invite returns success and refreshes the existing record
- Owner removal returns a clear 4xx response
- Unauthenticated requests follow existing auth handling

## Testing

Backend tests should cover:

- Listing members on an empty team seeds the current user as owner
- Inviting an existing user creates an active member row
- Inviting an unknown email creates a pending invite row
- Re-inviting the same email does not duplicate records
- Removing a member works for non-owner rows
- Removing the owner is rejected

Frontend verification should cover:

- Team page renders backend data
- Invite form submits successfully
- Pending invites display distinctly from active members

## Implementation Notes

Suggested backend files:

- `backend/app/modules/team/models.py`
- `backend/app/modules/team/schemas.py`
- `backend/app/modules/team/repository.py`
- `backend/app/modules/team/service.py`
- `backend/app/modules/team/router.py`
- `backend/app/modules/team/dependencies.py`

Suggested frontend touchpoints:

- `frontend/src/app/(workspace)/team/page.tsx`
- `frontend/src/components/workspace/workspace-module-pages.tsx`

## Open Decisions Resolved

- Use email as the invite identifier
- Prefer a lightweight pending invite model over real email delivery
- Keep the current single-workspace assumption
- Keep role management minimal

