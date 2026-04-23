######################
RSP user notifications
######################

.. abstract::

   During operations of the Rubin Science Platform, we will frequently need to communicate with users, either collectively or individually. These communications include welcome pages and tool tips, broadcast messages, and per-user messages about usage or other specific issues. This technote proposes a technical framework for these user notifications and discusses related issues around analysis of user activity.

Requirements
============

Types of notifications
----------------------

There are several different types of user notifications that will need separate treatment:

- Welcome and introductory messages.
  These are presented to the user the first time or first few times they access a particular service or feature.
  The user should be able to dismiss the message so that it doesn't appear in the future, or dismiss all such help messages if they are annoyed by this communication method.
  Users should also be able to reset the dismissal and see such messages again as if they were a new user, which may be desirable if they have not used the Rubin Science Platform for some time and want a refresher.

- Broadcast messages to all users.
  These messages are currently handled by Semaphore_.
  Broadcast messages need to support scheduled and recurring broadcast messages, levels of severity (currently we have three), and per-user dismissal so that a user can indicate that they don't want to see that broadcast message again.
  Some broadcast messages may be sufficiently important that we don't want to allow dismissal, such as ongoing outage notifications.

  .. _Semaphore: https://semaphore.lsst.io/

- Application-initiated messages to individual users.
  Applications may need some way to notify a user of something specific to that user.
  For example, an application may want to report when a long-running background job or query has completed.

- Administrator-initiated messages to individual users.
  Rubin Science Platform administrators will need to send notifications to specific users about their use of the platform, availability of new features that user specifically requested, or queries about unusual usage patterns.
  Allowing user responses to queries would be a nice additional feature, but is not discussed further in this initial design.

- Metrics-based usage and quota alerts.
  For example, notifying a user that the are at 90% or 100% of their disk quota, or that their API calls have been automatically throttled due to hitting a quota limit.
  A special case of this, discussed :ref:`further below <metrics-actions>`, is automatically analyzing user usage patterns and setting tighter quotas or throttling their usage if their usage seems excessive over an extended period of time beyond the window of simple API throttling.

Formatting notifications
------------------------

Notifications should support Markdown formatting, similar to the existing broadcast notifications supported by Semaphore_.
They should have a short summary and a larger body that can be expanded for more details.

Displaying notifications
------------------------

Notifications should, by default, be shown to the user via a notifications area on the home page of the Rubin Science Platform, provided by Squareone_.
Following the now-common design of many web sites, the initial proposed design is a bell icon with a red count badge of unread messages (if any).
Clicking the icon brings up the user's notifications, read and unread.
It may be useful to have a "See all notifications" link that goes to a separate page that can display more history.

.. _Squareone: https://squareone.lsst.io/

Some notifications, such as the current broadcast messages, should instead or in addition be shown as banner messages at the top of the home page.
Broadcast notifications should be configurable for whether they are displayed as banners, as user notifications, or both, and whether they are dismissable.

Notifications specific to a particular aspect, such as welcome and introduction screens, should only be shown within that aspect.

In the future, we may also want to integrate notifications with the Discourse discussion forums at community.lsst.org_ so that the user can receive direct messages for important notifications, thus triggering email notification.
This would require some way of mapping RSP users to Discourse users.

.. _community.lsst.org: https://community.lsst.org/

Alternately, we may want to send the most important notifiations to the user via email.

Browser notifications
---------------------

Most browsers now support `browser notifications`_, which allow users to permit web sites to send notifications even if that site is not currently loaded.
Squareone should add support for providing user notifications via browser notifications.
This is a lower priority than providing the notification icon and interactive browser interface.

.. _browser notifications: https://developer.mozilla.org/en-US/docs/Web/API/Notification

Clearing notifications
----------------------

In most cases, users should be able to dismiss any banner notification or welcome message.
That notification should then not be shown to that user again, but, for banner messages, will still appear in their notification history.

Notifications should be removed if the issue prompting the notification has been resolved.
For example, if a user is being rate-limited due to quotas and their quota is increased or their number of requests drops so that they are no longer being rate-limited, the corresponding notification should be suppressed automatically and fairly quickly to avoid misleading the user.

Notifications may also have an expiration time, and should not be displayed to the user after that time.

Proposed design
===============

The proposed design builds on the existing Semaphore_ service, expanding it to provide a REST API to notification publishers as well as UIs that want to display notifications.

.. diagrams:: architecture.py

Applications, metrics analysis cron jobs, and administrators can all create notifications via the REST API, which are stored in a database.
UIs such as Squareone_ query for notifications via a separate REST API, and can tell that REST API when a user has dismissed a notification or requested that welcome and introductory messages not be shown.

This diagram includes Nublado and the Portal Aspect as UIs, since at least they may want to use the welcome and introductory message support, but in the initial design all notifications will be shown by Squareone.

Data model
----------

There are two high-level possibilities for the data model for application- and metrics-triggered user notifications:

#. The originating application constructs a formatted message to the user and sends that to Semaphore.
   Semaphore stores the originating application, target user (if not broadcast), and a unique notification identifier, but otherwise works only with formatted messages.

#. The originating application sends structured data to Semaphore, which stores the original structured data by type of notification.
   Semaphore is responsible for turning that structured data into a formatted message for the user that is handed to UIs when they query Semaphore for user notifications.

Both approaches have advantages and disadvantages.
The first makes it easier to add new notifications, since no changes to Semaphore are required.
The second decouples message formatting from the structured application messages and allows applications to ignore presentation issues and focus only on the relevant semantic information to put into the notification.
The second approach also stores structured data about each notification, which may be useful for secondary analysis.
However, it requires changes to both Semaphore and the originating application when adding new alerts, including in many cases a new Semaphore route, models, and database migration to add a new table for a new type of structured alert data.

The benefits of structured notification data and collecting all formatting and user presentation issues in Semaphore feels more significant than the additional maintenance burden of changing Semaphore for each new type of user notification, particularly since we have found ways to mostly automate generation of database migrations.
We therefore plan to use the second approach.
This also allows all user notification templates to be collected in one place, either Semaphore configuration in Phalanx or possibly a Git repository similar to how broadcast alerts are handled now, for ease of review and cross-notification changes.

However, we will not proliferate types of alerts unnecessarily.
Alerts that mostly share the same structured data can be unified, and multiple applications can submit the same general type of alerts.
The API should therefore partition the REST view of the alert data by application so that each application only sees its own alerts when listing existing alerts (during alert reconciliation, for example).

Authentication
--------------

Requests to Semaphore from applications and cron jobs authenticate with internal application credentials, generally created via Kubernetes ``GafaelfawrServiceToken`` custom resources.
As an optimization, the cron jobs that analyze metrics may run as part of the Semaphore Phalanx application and thus talk to the Semaphore database directly instaed of going through the REST API.

Requests to Semaphore from UIs are either unauthenticated, for unauthenticated users who only see universal broadcast messages, or are authenticated with the user's token via normal Gafaelfawr_ delegated authentication.
For unauthenticated users, no notification bell icon is shown and any broadcast messages are shown as banners, similar to the current behavior of Squareone.

.. _Gafaelfawr: https://gafaelfawr.lsst.io/

.. _metrics-actions:

Taking actions based on metrics
-------------------------------

Many of the usage policies that we may wish to impose are not easy to calculate inside individual applications without retaining a lot of state.
For example, we may be happy for a user to perform lots of Butler queries and pull lots of images when they are actively working on an analysis, but we may not want users to automate the download of millions of images.
Distinguishing between these cases in the Butler server would require tracking per-user usage counters, which would be annoying additional state tracking.

We already export per-user statistics of this type to InfluxDB via Sasquatch_.
Rather than add additional state tracking to each application, and find a way to do cross-application state tracking where relevant, we can instead trigger such actions from InfluxDB queries.

.. _Sasquatch: https://sasquatch.lsst.io/

The first anticipated use case of this type of query and action is to look for users who are consuming excessive platform resources by making expensive requests below the quota limits for extended periods of time, such as via automation.
A design of such a system could look like this:

#. Search for potentially abusive users with an InfluxDB query for a threshold of total traffic volume.
#. Set a lower quota for such users via a new Gafaelfawr API.
#. Impose that quota inside the relevant service.
#. Notify the user using the application API to the notification system.
#. Record that this user has been throttled or use the Gafaelfawr API to find throttled users, whichever approach seems easiest to maintain.
#. Repeat this process periodically.
   If a user was previously throttled and no longer needs to be based on some new threshold, remove the quota restriction and the notification.

User interfaces
---------------

Squareone_ already has a mechanism for displaying banner notifications using the existing Semaphore API.
To show the new notification icon on the front page, it should make an authenticated request rather than an unauthenticated request and thereby get both banners and the user's current notifications and unread count.
The Semaphore API should be designed to return the information necessary for generating the home page of Squareone in a single response.

When the user requests their full notification history, that response may be paginated depending on the number of notifications that user has received.
Very old notifications may be discarded to avoid indefinite database growth.

Semaphore will need correct handling of CORS preflight checks to allow authenticated requests, since Semaphore may be in a different origin than Squareone going forward.

The Semaphore API for user interfaces should return the notifications rendered in HTML so that the various user interfaces don't have to handle the conversion from Markdown.

Welcome and introductory messages
---------------------------------

Although welcome and introductory messages are similar to broadcast user notifications, including the ability of individual users to dismiss the notification for themselves, they should use a separate API in Semaphore.
They may not be displayed in the same places or in the same ways.
In the future (not in the initial implementation), they may be attached to particular portions or features of the UI instead of a general welcome message or splash screen.

To replace the current Nublado_ landing page with a better-behaved welcome screen, we will add a JupyterLab extension that sends an authenticated query to Semaphore on startup for any relevant welcome message and, if any is returned, displays it.
That should use a different mechanism than the current approach of changing the home tab of the UI so that it can be a modal dialogue with an option to never see the message again.

.. _Nublado: https://nublado.lsst.io/

Firefly, which provides the Portal aspect, currently has a limited facility to show a static banner message to users, but no support for dynamic user notifications.
We will not be adding any further notification support to Firefly for this first round of development, but may consider it in the future.

Discussion
==========

Message bus versus API
----------------------

On first glance, application-triggered notifications seemed like a natural fit for a message bus such as Kafka.
Applications could send a notification message, which would then be consumed by some other service and added to the user's notifications list and API results used by UIs that display notifications.

The problem with this design comes with revoking notifications.
Message buses are best for fire-and-forget messages that the sender does not have to interact with further.
This notification design requires that applications be able to revoke their notifications when the condition prompting the notification has gone away.

This can be done via a message bus with a subsequent cancellation message sent over the same message bus, but this would require assigning unique identifiers to notifications and tracking those in the application so that it can look up and revoke a notification.
It would also make it hard for the application to reconcile its current notification state with the service that provides notifications to UIs.

Given that, we decided we needed a more conventional REST API to a central notification service, which will allow each application to list its currently active notifications and revoke the ones that are no longer appropriate.
Since the REST API would be needed anyway, it makes sense to also create notifications in the same way rather than splitting the API across multiple protocols.

Why not email from the start?
-----------------------------

Historically, notifications from other services were often done via email.
The data.lsst.cloud instance of the Rubin Science Platform does collect and verify email addresses for each user.
However, email is an unattractive default choice for operational designs in 2026 for several reasons:

#. Email spam and therefore email spam protection has become increasingly aggressive.
   Best practice for sending email is now to use a dedicated email service (increasing cost) that verifies the sender to increase the likelihood of successful delivery, and even when using such a service, a lot of email is filtered out as spam by major email providers.

#. The increase in phishing and other email-based attacks has made users rightfully more skeptical of email.
   Even if we can establish that email is genuine, conscientious users have to waste time and mental resources analyzing the email to ensure that it is valid.

#. Email is a separate context from the user's work in the Rubin Science Platform and may not be timely or accessible while they're working within the platform.

#. There is a long, slow decline of use of email for communications.
   Some users, particularly younger users, may not check email frequently.

We currently use banners on RSP home page for broadcast notifications.
Building on this approach as the first implementation step seems better-tailored to the notification needs of the RSP.
The notification is put in front of the user where they are working, and it clearly comes from the RSP and is not phishing.
Users who only use APIs from outside the RSP aren't reachable this way, however.

Email notifications would be valuable as a separate, additional notification path, particularly for important messages we don't want the user to miss even if they are not actively using the RSP.
We may therefore provide email notification for some subset of notifications as part of later development work.
Options include using community.lsst.org direct messages, sending the email directly through some email sending provider, or enrolling users in a ticketing system so that we can create tickets and list the user as a notification contact.
