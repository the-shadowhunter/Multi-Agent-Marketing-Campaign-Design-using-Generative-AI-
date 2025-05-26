# streamlit_chat_stable.py
import os
import streamlit as st
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from dotenv import load_dotenv
import autogen
import time

# Load environment variables
load_dotenv()
print("DEBUG: Loading environment variables...")

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="Marketing Debate Chat", layout="centered")
st.title("💬 Marketing Campaign Debate")
st.caption("AI agents collaborating to design a campaign. Results appear after completion.")

# --- LLM Configuration ---
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    st.error("GROQ_API_KEY not found. Please set it in your environment variables or a .env file.")
    st.stop()
else:
    print("DEBUG: GROQ API Key loaded.")

llm_config = {
    "config_list": [
        {
            "model": "llama3-70b-8192",
            "base_url": "https://api.groq.com/openai/v1",
            "api_key": api_key,
        }
    ],
    "temperature": 0.70,
    "timeout": 180,
    "cache_seed": None,
}

# --- Agent Styles (using emojis for avatars) ---
AGENT_AVATARS = {
    "Content_Writer": "✍️",
    "Graphic_Designer": "🎨",
    "Data_Analyst": "📊",
    "Brand_Manager": "🏷️",
    "User_Proxy": "👤",
    "chat_manager": "🧑‍💼",
    "Unknown": "🤖"
}

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "discussion_running" not in st.session_state:
    st.session_state.discussion_running = False
if "discussion_completed" not in st.session_state:
    st.session_state.discussion_completed = False
if "initial_task_text" not in st.session_state:
    st.session_state.initial_task_text = ""

# --- UI Input Elements ---
st.write("---")
product_name = st.text_input(
    "Product Name:",
    "QuantumPulse Smartwatch",
    key="product_input",
    disabled=st.session_state.discussion_running
)
campaign_goal = st.text_area(
    "Brief Campaign Goal:",
    f"Develop a launch campaign for the new '{st.session_state.get('product_input', 'QuantumPulse Smartwatch')}' targeting young, tech-savvy professionals. Highlight its sleek design and advanced health tracking.",
    key="goal_input",
    height=100,
    disabled=st.session_state.discussion_running
)

# --- Function to generate initial task ---
def get_initial_task(product, goal):
    return f"""
Let's design a marketing campaign for the launch of the '{product}'.
Goal: {goal}.
Key aspects to cover: Target audience refinement, core messaging (Content_Writer), visual identity (Graphic_Designer), data-driven justification (Data_Analyst), and overall brand alignment (Brand_Manager).
Remember our internal style debate: Graphic_Designer, you advocate for bold/neon visuals. Brand_Manager, you must uphold the minimalist/elegant brand aesthetic. Data_Analyst, provide insights on which style might resonate better.
Let's debate and synthesize these ideas into a cohesive plan. Conclude by summarizing the agreed approach. The final output should be a summarized campaign plan. Make sure the Brand_Manager ensures the final summary is created. Ensure the conversation concludes within the allowed rounds. If approaching the limit, Brand_Manager should summarize proactively.
"""

if not st.session_state.discussion_running:
    st.session_state.initial_task_text = get_initial_task(
        st.session_state.get('product_input', 'QuantumPulse Smartwatch'),
        st.session_state.get('goal_input', f"Develop a launch campaign...")
    )

# --- Control Buttons ---
col_btn1, col_btn2 = st.columns([1, 5])
with col_btn1:
    start_button = st.button(
        "▶️ Start",
        use_container_width=True,
        disabled=st.session_state.discussion_running or not product_name or not campaign_goal
    )
    reset_button = st.button(
        "🔄 Reset",
        use_container_width=True,
        disabled=st.session_state.discussion_running
    )

st.write("---")
st.subheader("Conversation Log")

# --- Chat Display Area ---
chat_container = st.container(height=500, border=True)
with chat_container:
    if not st.session_state.messages:
        st.caption("*(Campaign discussion will appear here after clicking Start and waiting for completion...)*")
    else:
        for msg in st.session_state.messages:
            sender_name = msg.get("role", "Unknown")
            lower_sender_name = sender_name.lower()
            found_avatar = False
            for agent_name in AGENT_AVATARS:
                if lower_sender_name == agent_name.lower():
                    avatar = AGENT_AVATARS.get(agent_name, "🤖")
                    found_avatar = True
                    break
            if not found_avatar:
                print(f"WARN: Sender name '{sender_name}' not in AGENT_AVATARS. Using Unknown.")
                avatar = AGENT_AVATARS.get("Unknown", "🤖")

            with st.chat_message(name=sender_name, avatar=avatar):
                display_name = msg.get("role", "Unknown")
                display_content = f"**{display_name}:** {msg['content']}"
                st.markdown(display_content, unsafe_allow_html=True)

# --- Callback Function (for TERMINAL LOGGING ONLY now) ---
def message_logging_callback(recipient, messages, sender, config):
    if not messages: return False, None
    last_message = messages[-1]
    content = last_message.get("content", "")
    message_sender_name = last_message.get("name") or last_message.get("role")
    if not message_sender_name:
        sender_object_name = getattr(sender, 'name', 'Unknown')
        final_sender_name = sender_object_name
    else:
        final_sender_name = message_sender_name

    if content and content.strip() and "Campaign plan summary complete".lower() not in content.lower():
        print(f"DEBUG_CALLBACK: Sender: '{final_sender_name}'. Content: '{content[:80]}...'")
    else:
        print(f"DEBUG_CALLBACK: Skipped logging for '{final_sender_name}' (empty/terminate).")

    return False, None

# --- Agent Initialization (Cached) ---
@st.cache_resource
def initialize_agents():
    print("DEBUG: Initializing agents...")
    designer_preference = "bold, eye-catching neon themes"
    manager_preference = "minimalist and elegant aesthetics (clean, simple)"

    content_writer = AssistantAgent(
        name="Content_Writer",
        system_message=(
            "You are a skilled Content Writer. Your task is to craft compelling, clear, and benefit-focused "
            "marketing copy for the QuantumPulse Smartwatch targeting young, tech-savvy professionals. "
            "Focus on its sleek design and advanced health tracking features. Collaborate with the team "
            "to ensure the messaging aligns with the final campaign direction."
        ),
        llm_config=llm_config
    )
    graphic_designer = AssistantAgent(
        name="Graphic_Designer",
        system_message=(
            f"You are an innovative Graphic Designer known for modern, attention-grabbing visuals. "
            f"You strongly advocate for using '{designer_preference}' for the QuantumPulse campaign to appeal "
            f"to the tech-savvy audience and cut through the noise. Provide strong arguments for your design choices, "
            f"but be prepared to discuss and potentially adapt based on team feedback and data."
        ),
        llm_config=llm_config
    )
    data_analyst = AssistantAgent(
        name="Data_Analyst",
        system_message=(
            f"You are a meticulous Data Analyst. Your role is to provide objective, data-driven insights. "
            f"Analyze the target audience (young, tech-savvy professionals) and evaluate the potential "
            f"market resonance of '{designer_preference}' versus the brand's standard '{manager_preference}'. "
            f"Use market trends, competitor analysis, or hypothetical A/B testing rationale to support your "
            f"recommendations. Focus on which style is likely to perform better for the campaign goals."
        ),
        llm_config=llm_config
    )
    brand_manager = AssistantAgent(
        name="Brand_Manager",
        system_message=(
            f"You are the Brand Manager, responsible for the overall brand strategy and consistency. "
            f"Ensure the QuantumPulse campaign aligns with the established '{manager_preference}' brand aesthetic. "
            f"Mediate the discussion, especially the design style debate between the Graphic Designer and Data Analyst. "
            f"Guide the team towards a cohesive plan that is both effective and brand-appropriate. "
            f"You have the final say on brand alignment and must ensure a final summary plan is produced before the chat ends. "
            # "If the max round limit is approaching, take initiative to summarize. Once the final summary is displayed, say \"Campaign plan summary complete.\""
        ),
        llm_config=llm_config
    )
    print("DEBUG: Agents initialized.")
    return content_writer, graphic_designer, data_analyst, brand_manager

# --- Main Execution Flow ---
if reset_button and not st.session_state.discussion_running:
    print("DEBUG: Reset button clicked.")
    st.session_state.messages = []
    st.session_state.discussion_running = False
    st.session_state.discussion_completed = False
    default_product = "QuantumPulse Smartwatch"
    default_goal = f"Develop a launch campaign for the new '{default_product}' targeting young, tech-savvy professionals. Highlight its sleek design and advanced health tracking."
    st.session_state.product_input = default_product
    st.session_state.goal_input = default_goal
    st.session_state.initial_task_text = get_initial_task(default_product, default_goal)

    try:
        initialize_agents.clear()
        print("DEBUG: Agent cache cleared.")
    except AttributeError:
        print("DEBUG: st.cache_resource clear() method not available.")
    st.rerun()

if start_button and not st.session_state.discussion_running:
    print("DEBUG: Start button clicked.")
    st.session_state.initial_task_text = get_initial_task(
        st.session_state.product_input,
        st.session_state.goal_input
    )
    st.session_state.discussion_running = True
    st.session_state.discussion_completed = False
    st.session_state.messages = []
    st.rerun()

if st.session_state.discussion_running:
    print("DEBUG: Entering discussion running block.")
    groupchat = None
    manager = None
    with st.spinner("Agents are discussing... Please wait for results to appear below."):
        try:
            content_writer, graphic_designer, data_analyst, brand_manager = initialize_agents()
            agents = [content_writer, graphic_designer, data_analyst, brand_manager]

            user_proxy = UserProxyAgent(
                name="User_Proxy",
                human_input_mode="NEVER",
                is_termination_msg=lambda x: "Campaign plan summary complete".lower() in x.get("content", "").lower(),
                max_consecutive_auto_reply=2,
                code_execution_config=False,
                system_message="You are the initiator. Provide the task, then observe.",
            )

            print("DEBUG: Registering message logging callback...")
            all_involved_agents = agents + [user_proxy]
            for agent in all_involved_agents:
                agent.register_reply(
                    autogen.Agent,
                    reply_func=message_logging_callback,
                    config=None,
                    reset_config=True
                )
            print("DEBUG: Logging callbacks registered.")

            print("DEBUG: Creating GroupChat and Manager...")
            groupchat = GroupChat(
                agents=all_involved_agents,
                messages=[],
                max_round=15,
                speaker_selection_method="auto",
                allow_repeat_speaker=False,
                send_introductions=True,
            )
            manager = GroupChatManager(
                groupchat=groupchat,
                llm_config=llm_config,
                name="chat_manager",
                is_termination_msg=lambda x: "Campaign plan summary complete".lower() in x.get("content", "").lower(),
                system_message=(
                    "You are the chat manager. Facilitate the discussion to develop the marketing plan. "
                    "Ensure the Brand_Manager provides a final summary before the max_round limit is hit or a Campaign plan summary complete message is received."
                )
            )
            print("DEBUG: GroupChat and Manager created.")

            initial_task = st.session_state.initial_task_text
            print(f"DEBUG: Initiating chat via User_Proxy with task: '{initial_task[:100]}...'")

            user_proxy.initiate_chat(
                manager,
                message=initial_task
            )
            print("DEBUG: initiate_chat finished.")

        except Exception as e:
            print(f"ERROR: An error occurred during chat execution: {e}", exc_info=True)
            st.error(f"An error occurred during the chat: {e}")
        finally:
            print("DEBUG: Entering finally block.")
            if groupchat:
                print(f"DEBUG: Retrieving final messages from groupchat. Total: {len(groupchat.messages)}")
                final_ui_messages = []
                for msg in groupchat.messages:
                    sender_name = msg.get("name", msg.get("role", "Unknown"))
                    content = msg.get("content", "")
                    if content and content.strip():
                        if sender_name not in AGENT_AVATARS:
                            print(f"WARN: Mapping final message sender '{sender_name}' to 'Unknown' for UI.")
                            role_for_ui = "Unknown"
                        else:
                            role_for_ui = sender_name
                        final_ui_messages.append({"role": role_for_ui, "content": content})

                st.session_state.messages = final_ui_messages
                print(f"DEBUG: Updated st.session_state.messages with {len(final_ui_messages)} final messages.")
            else:
                print("WARN: Groupchat object not available in finally block.")

            st.session_state.discussion_running = False
            st.session_state.discussion_completed = True
            print("DEBUG: Set running=False, completed=True.")

            st.rerun()

if st.session_state.discussion_completed and not st.session_state.discussion_running:
    st.success("Agent discussion finished!")
    print("DEBUG: Displaying 'Discussion finished!' message.")