# n8n AI Automation Projects

This repository documents three n8n workflow assignments built around
Telegram, AI agents, search tools, memory, and Google Workspace
integrations.

## Projects at a glance

  -----------------------------------------------------------------------
  Assignment              Project                 Main purpose
  ----------------------- ----------------------- -----------------------
  1                       Amazon Telegram Agent   A Telegram-based
                                                  shopping assistant that
                                                  can search
                                                  Amazon-related
                                                  information using
                                                  SerpApi.

  2                       Multi-Agent             A Telegram AI assistant
                          Productivity Assistant  connected to Google
                                                  Search and Google
                                                  Workspace tools such as
                                                  Gmail, Calendar, Docs,
                                                  and Sheets.

  3                       Jarvis -- Telegram      A Telegram assistant
                          Voice Assistant         that accepts voice or
                                                  text input, transcribes
                                                  voice messages, and
                                                  responds with text or
                                                  generated audio while
                                                  using productivity
                                                  tools.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## Assignment 1: Amazon Telegram Agent

**Workflow:** [Open in
n8n](https://n8n-2fqi.srv2061895.hstgr.cloud/workflow/QKBD2DlqtgJDVERP)

### Short description

A Telegram-based AI shopping assistant built with n8n, OpenAI, Simple
Memory, and SerpApi. It interprets user messages, searches for
Amazon-related information when needed, and returns a response through
Telegram.

### Objective

Create a conversational shopping assistant that lets a user ask
product-related questions through Telegram and receive an AI-generated
response informed by search results.

### Workflow flow

1.  **Telegram Trigger** --- Starts the workflow when a Telegram message
    is received.
2.  **AI Agent** --- Interprets the user's request and decides how to
    respond or whether to use a connected tool.
3.  **OpenAI Chat Model** --- Provides the language-model capability
    used to understand the request and generate a response.
4.  **Simple Memory** --- Supplies conversation context to support
    follow-up questions during the configured memory session.
5.  **Amazon search in SerpApi** --- Provides an Amazon-focused search
    capability that the agent can use to retrieve relevant
    product/search information.
6.  **Send a text message** --- Sends the agent's response back to the
    user in Telegram.

### Concepts demonstrated

-   Event-driven automation using a Telegram trigger
-   AI agent orchestration and tool calling
-   Large Language Model (LLM) integration with OpenAI
-   Conversational context using memory
-   External search/API integration through SerpApi
-   Returning automated responses through a messaging platform

### Example use case

A user asks about a product or wants to find Amazon listings. The AI
agent interprets the question, uses the Amazon search tool when
appropriate, and replies in Telegram with the resulting information.

------------------------------------------------------------------------

## Assignment 2: Multi-Agent Productivity Assistant

**Workflow:** [Open in
n8n](https://n8n-2fqi.srv2061895.hstgr.cloud/workflow/znp479v9igxgilBu)

### Short description

A Telegram-based AI productivity assistant built with n8n and OpenAI. It
combines conversational memory with Google Search and Google Workspace
tools, enabling the agent to help with information lookup and supported
productivity actions involving Gmail, Google Calendar, Google Docs, and
Google Sheets.

### Objective

Build a single conversational entry point where users can request
information or supported productivity tasks without manually opening
each connected application.

### Workflow flow

1.  **Telegram Trigger** --- Receives the user's message and starts the
    workflow.
2.  **AI Agent** --- Understands the request and determines which
    connected tool, if any, is appropriate.
3.  **OpenAI Chat Model** --- Interprets the request and generates the
    response or tool instructions.
4.  **Simple Memory** --- Provides conversation context for follow-up
    messages within the configured session.
5.  **Google Search in SerpApi** --- Allows the agent to search the web
    for relevant information.
6.  **Google Docs** --- Supports document creation based on the
    configured node operation.
7.  **Google Calendar** --- Supports event creation based on the
    configured node operation.
8.  **Google Sheets** --- Supports appending or updating sheet data
    based on the configured operation.
9.  **Gmail** --- Supports sending an email based on the configured node
    operation.
10. **Send a text message** --- Returns a response to the user through
    Telegram.

### Concepts demonstrated

-   AI agent tool selection and orchestration
-   Connecting multiple third-party services in one workflow
-   Google Workspace automation
-   Web search integration
-   Conversational memory
-   Natural-language requests as an interface to productivity workflows

### Example use case

A user sends a request through Telegram, such as asking for information,
drafting or creating a document, creating a calendar event, updating a
spreadsheet, or sending an email. The agent can use the connected tools
relevant to the request and then respond through Telegram.

**Important:** The exact action performed by each Google Workspace node
depends on its configuration and the permissions of the connected
account. Review node settings and test each action before using the
workflow with important data.

------------------------------------------------------------------------

## Assignment 3: Jarvis -- Telegram Voice Assistant

**Workflow:** [Open in
n8n](https://n8n-2fqi.srv2061895.hstgr.cloud/workflow/A883zOlkf3LcgqV2)

### Short description

Jarvis is a Telegram-based voice and text AI assistant built with n8n
and OpenAI. It detects whether a Telegram message contains a voice note,
downloads and transcribes audio using Whisper, passes the resulting text
to an AI agent, and returns either a text response or generated voice
reply. The agent also has access to search, Gmail, Google Docs, Google
Sheets, and Google Calendar tools.

### Objective

Create a hands-free, conversational assistant that can process voice or
text input and help with common information and productivity tasks
through Telegram.

### Workflow flow

1.  **Telegram Trigger** --- Receives incoming Telegram messages.
2.  **Is Voice Note?** --- Routes the message based on whether it
    contains a voice note.
3.  **Voice branch: Download Voice Note** --- Downloads the Telegram
    voice file.
4.  **Transcribe Voice (Whisper)** --- Converts the voice recording into
    text using speech recognition.
5.  **Voice Input** --- Provides an input/editing step for the
    transcribed text before it is passed to the agent.
6.  **Text branch: Text Input** --- Handles text messages directly.
7.  **Jarvis AI Agent** --- Processes either the transcribed voice text
    or the user's text message and decides whether connected tools are
    needed.
8.  **OpenAI Chat Model and Jarvis Memory** --- Provide language-model
    reasoning and conversational context.
9.  **Connected tools** --- Include web search, Gmail send and search
    operations, Google Docs creation and writing, Google Sheets row
    updates and reads, and Google Calendar event creation and retrieval,
    as shown in the workflow.
10. **Reply as Voice?** --- Routes the agent's result according to
    whether a voice reply is requested.
11. **Voice response branch: Jarvis Voice (TTS)** --- Generates audio
    from the assistant's response.
12. **Send Voice Reply** --- Sends the generated audio to Telegram.
13. **Text response branch: Send Text Reply** --- Sends a text response
    to Telegram.

### Concepts demonstrated

-   Voice and text input handling
-   Conditional branching with an IF-style routing node
-   Audio file retrieval from Telegram
-   Speech-to-text transcription using Whisper
-   AI agent orchestration with tools
-   Text-to-speech audio generation
-   Conversation memory
-   Integration with Google Workspace and search
-   Returning different response formats through Telegram

### Example use case

A user sends Jarvis a voice note asking a question or requesting a
supported task. The workflow downloads and transcribes the audio, sends
the text to the AI agent, and returns an answer. Depending on the
routing choice, the answer is delivered as a Telegram text message or a
generated voice reply.

------------------------------------------------------------------------

## Shared architecture and key concepts

Across the three assignments, the main architecture is:

**Telegram input → AI processing → optional tool/API calls → response
delivered through Telegram**

The workflows demonstrate these core concepts:

-   **Trigger-based automation:** Incoming Telegram messages initiate
    workflow execution.
-   **LLM integration:** OpenAI models interpret natural-language
    requests and generate responses.
-   **AI agent tool use:** An agent can select from the tools connected
    to it based on the user's request.
-   **Memory:** Simple Memory nodes provide conversational context
    according to their configuration.
-   **API and app integrations:** SerpApi and Google Workspace nodes
    connect the workflow to external services.
-   **Conditional routing:** The Jarvis workflow separates voice and
    text messages and chooses a response path.
-   **Multimodal interaction:** Jarvis combines text processing, audio
    transcription, and audio generation.


## Prerequisites and setup notes

Before running these workflows, confirm that:

-   Telegram bot credentials are configured correctly.
-   OpenAI credentials and the selected model are available.
-   SerpApi credentials are configured for the search tools.
-   Google account credentials and permissions are configured for the
    Google Workspace nodes.
-   The Telegram bot can receive messages and send the intended response
    type.
-   The Jarvis voice workflow has access to the required audio
    transcription and text-to-speech operations.
-   Memory/session settings are suitable for the desired conversation
    behavior.

## Testing checklist

-   [ ] Send a basic text message to each Telegram bot/workflow.
-   [ ] Confirm that the AI agent returns a relevant response.
-   [ ] Test a search request in Assignments 1 and 2.
-   [ ] Test each required Google Workspace action in Assignment 2.
-   [ ] Test voice-note transcription in Assignment 3.
-   [ ] Test both text and voice response paths in Assignment 3.
-   [ ] Review execution logs and confirm that each node succeeds.
-   [ ] Verify credentials, permissions, and output before using real or
    sensitive data.

## Project links

1.  [Assignment 1 --- Amazon Telegram
    Agent](https://n8n-2fqi.srv2061895.hstgr.cloud/workflow/QKBD2DlqtgJDVERP)
2.  [Assignment 2 --- Multi-Agent Productivity
    Assistant](https://n8n-2fqi.srv2061895.hstgr.cloud/workflow/znp479v9igxgilBu)
3.  [Assignment 3 --- Jarvis Telegram Voice
    Assistant](https://n8n-2fqi.srv2061895.hstgr.cloud/workflow/A883zOlkf3LcgqV2)
