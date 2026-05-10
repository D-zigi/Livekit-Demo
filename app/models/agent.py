"""
Agent CRUD models
"""
from typing import Optional, Literal, Dict
from pydantic import BaseModel, Field

from app.types import BusinessScopedReadModel, CallDirection

# Generic types used across multiple models
Gender = Literal["male", "female", "neutral"]

# Models
Model = str
VoiceModel = Literal[
    # Female voices
    "Achernar", "Aoede", "Autonoe", "Callirrhoe", "Despina", "Erinome",
    "Gacrux", "Kore", "Laomedeia", "Leda", "Pulcherrima", "Sulafat",
    "Vindemiatrix", "Zephyr",
    # Male voices
    "Achird", "Algenib", "Algieba", "Alnilam", "Charon", "Enceladus",
    "Fenrir", "Iapetus", "Orus", "Puck", "Rasalgethi", "Sadachbia",
    "Sadaltager", "Schedar", "Umbriel", "Zubenelgenubi",
]

# All All BCP-47 Code languages officially supported by Gemini Live
GeminiLiveLanguage = Literal[
    "ar-EG", "bn-BD", "nl-NL", "en-IN", "en-US", "fr-FR", "de-DE", "hi-IN",
    "id-ID", "it-IT", "ja-JP", "ko-KR", "mr-IN", "pl-PL", "pt-BR", "ro-RO",
    "ru-RU", "es-US", "ta-IN", "te-IN", "th-TH", "tr-TR", "uk-UA", "vi-VN"
]
# BCP-47 Code mapping for Gemini Live languages
GeminiLiveLanguageMap: dict[GeminiLiveLanguage, str] = {
    "ar-EG": "Arabic (Egyptian)",
    "bn-BD": "Bengali (Bangladesh)",
    "nl-NL": "Dutch (Netherlands)",
    "en-IN": "English (India)",
    "en-US": "English (US)",
    "fr-FR": "French (France)",
    "de-DE": "German (Germany)",
    "hi-IN": "Hindi (India)",
    "id-ID": "Indonesian (Indonesia)",
    "it-IT": "Italian (Italy)",
    "ja-JP": "Japanese (Japan)",
    "ko-KR": "Korean (Korea)",
    "mr-IN": "Marathi (India)",
    "pl-PL": "Polish (Poland)",
    "pt-BR": "Portuguese (Brazil)",
    "ro-RO": "Romanian (Romania)",
    "ru-RU": "Russian (Russia)",
    "es-US": "Spanish (US)",
    "ta-IN": "Tamil (India)",
    "te-IN": "Telugu (India)",
    "th-TH": "Thai (Thailand)",
    "tr-TR": "Turkish (Turkey)",
    "uk-UA": "Ukrainian (Ukraine)",
    "vi-VN": "Vietnamese (Vietnam)",
}

# All BCP-47 Code languages supported by the application
Language = Literal["en-US", "es-ES", "he-IL", "ru-RU", "ar-EG", "ar-SA", "ar-AE", "ar-IL"]
# BCP-47 Code mapping for languages
LanguageMap: Dict[Language, str] = {
    "en-US": "English",
    "es-ES": "Spanish",
    "he-IL": "Hebrew",
    "ru-RU": "Russian",
    "ar-EG": "Arabic (Egypt)",
    "ar-SA": "Arabic (Saudi Arabia)",
    "ar-AE": "Arabic (UAE)",
    "ar-IL": "Arabic (Israel)"
}

AgentVisibility = Literal["public", "private", "template"] # Agent visibility types

class AgentCreate(BaseModel):
    """
    AgentCreate model used to
    Create a new agent
    """
    name: Optional[str] = Field(default=None, description="Name")
    avatar: Optional[str] = Field(default=None, description="Avatar")
    gender: Gender = Field(default="neutral", description="Gender")
    language: Language = Field(description="Language")
    voice_model: VoiceModel = Field(description="Voice model")
    voice_style: Optional[str] = Field(default=None, description="Voice style")
    strategy: Optional[str] = Field(default=None, description="Strategy")
    instructions: Optional[str] = Field(default=None, description="Instructions")
    opening_message: Optional[str] = Field(default=None, description="Opening message")
    model: Model = Field(default="gemini-live-2.5-flash-native-audio", description="Model")
    temperature: float = Field(default=0.8, ge=0, le=2, description="Improvization")
    visibility: AgentVisibility = Field(default="private", description="Visibility")

class AgentRead(AgentCreate, BusinessScopedReadModel):
    """
    AgentRead model used to
    Read an agent
    """
    business_id: Optional[str] = Field(default=None, description="Business ID")

class AgentUpdate(BaseModel):
    """
    AgentUpdate model used to
    Update an agent
    """
    id: str = Field(description="ID")
    name: Optional[str] = Field(default=None, description="Name")
    avatar: Optional[str] = Field(default=None, description="Avatar")
    gender: Optional[Gender] = Field(default=None, description="Gender")
    language: Optional[Language] = Field(default=None, description="Language")
    voice_model: Optional[VoiceModel] = Field(default=None, description="Voice model")
    voice_style: Optional[str] = Field(default=None, description="Voice style")
    strategy: Optional[str] = Field(default=None, description="Strategy")
    instructions: Optional[str] = Field(default=None, description="Instructions")
    opening_message: Optional[str] = Field(default=None, description="Opening message")
    model: Optional[Model] = Field(default=None, description="Model")
    temperature: Optional[float] = Field(default=None, ge=0, le=2, description="Improvization")
    visibility: Optional[AgentVisibility] = Field(default=None, description="Visibility")

class AgentDelete(BaseModel):
    """
    AgentDelete model used to
    Delete an agent
    """
    id: str = Field(description="ID")


class AgentDefaultRequest(BaseModel):
    """
    Agent default request model
    """
    business_id: Optional[str] = Field(default=None, description="Business ID")
    direction: CallDirection = Field(description="Call direction")
    phone_number: str = Field(description="Phone number")


class Agent(AgentRead):
    """
    Agent model
    """

class AgentBase(AgentCreate):
    """
    Agent base model
    """
