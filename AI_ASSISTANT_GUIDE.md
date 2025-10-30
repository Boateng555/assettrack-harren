# 🤖 AI Assistant for AssetTrack

## Overview
The AI Assistant is a smart chatbot that understands your entire AssetTrack system and can answer questions about employees, assets, handovers, and more. It's designed to be context-aware and can help users navigate and understand the system.

## Features

### 🧠 **Smart Context Awareness**
- Knows what page you're currently on
- Understands your user role and permissions
- Has access to real-time system data
- Can provide insights based on current context

### 🔍 **Intelligent Search**
- Natural language search for assets and employees
- Understands queries like "Show me all laptops" or "Find employees in Bremen"
- Provides relevant results with context
- Can search by asset type, location, status, and more

### 💡 **System Insights**
- Provides quick insights about system health
- Identifies assets needing attention
- Shows pending handovers
- Highlights unassigned assets

### 🎯 **Multiple Access Points**
- **Floating Button**: Blue circle button in bottom-right corner (always visible)
- **User Menu**: "AI Assistant" link in the user dropdown
- **Dedicated Page**: Full chat interface at `/ai-chat/`
- **Modal Chat**: Quick access from any page

## Setup Instructions

### 1. **Install Dependencies**
```bash
pip install openai>=1.0.0
```

### 2. **Configure API Key**
Add your OpenAI API key to your `.env` file:
```env
OPENAI_API_KEY=your-actual-openai-api-key-here
```

### 3. **Restart Server**
```bash
python manage.py runserver
```

### 4. **Test the Setup**
```bash
python setup_ai_assistant.py
python test_ai_assistant.py
```

## Usage Examples

### **Asset Queries**
- "Show me all laptops"
- "Find assets assigned to John"
- "What laptops are in Bremen office?"
- "Show me assets that need maintenance"
- "Find assets with health score below 50%"

### **Employee Queries**
- "Find employees in Bremen"
- "Show me all IT department employees"
- "Who has the most assets assigned?"
- "Find employees with pending handovers"

### **System Queries**
- "What are the pending handovers?"
- "How many assets are unassigned?"
- "Show me system statistics"
- "What's the asset distribution by office?"
- "Tell me about recent activity"

### **General Help**
- "How do I add a new asset?"
- "What is the handover process?"
- "How do I assign an asset to an employee?"
- "Explain the welcome pack system"

## Technical Details

### **AI Assistant Class** (`assets/ai_assistant.py`)
- `AssetTrackAI`: Main AI assistant class
- `get_context_data()`: Gets current page and user context
- `search_assets()`: Searches assets using natural language
- `search_employees()`: Searches employees using natural language
- `process_query()`: Processes user queries and returns AI responses
- `get_quick_insights()`: Generates system insights

### **Views** (`assets/views.py`)
- `ai_chat()`: Main chat interface
- `ai_quick_insights()`: API endpoint for quick insights
- `ai_search()`: API endpoint for search functionality

### **Templates**
- `templates/ai_chat.html`: Full chat interface
- `templates/base.html`: Floating button and modal chat

### **URLs** (`assets/urls.py`)
- `/ai-chat/`: Main chat page
- `/ai/quick-insights/`: Quick insights API
- `/ai/search/`: Search API

## API Integration

### **OpenAI Integration**
The AI assistant uses OpenAI's GPT-3.5-turbo model for natural language processing. It's configured to:
- Understand AssetTrack-specific context
- Provide helpful, professional responses
- Search and analyze your data
- Give actionable insights

### **Database Integration**
The AI assistant has access to:
- All asset data (name, type, status, location, health score)
- All employee data (name, department, office, contact info)
- Handover records and status
- Welcome pack information
- System statistics and analytics

## Customization

### **Adding New Capabilities**
To add new AI capabilities:

1. **Extend the AI Assistant class**:
```python
def new_capability(self, query):
    # Your custom logic here
    return result
```

2. **Add new search methods**:
```python
def search_custom_data(self, query):
    # Search your custom data
    return results
```

3. **Update the system prompt**:
```python
self.system_prompt = """
Your updated system prompt with new capabilities...
"""
```

### **Customizing Responses**
- Modify the `system_prompt` in `AssetTrackAI.__init__()`
- Update response formatting in `process_query()`
- Add custom search logic in search methods

## Troubleshooting

### **Common Issues**

1. **"AI processing error"**
   - Check if OpenAI API key is set correctly
   - Verify internet connection
   - Check API key permissions

2. **"No results found"**
   - Verify database has data
   - Check search query format
   - Ensure proper indexing

3. **"Error loading AI Assistant"**
   - Check Django server is running
   - Verify all dependencies installed
   - Check for JavaScript errors in browser console

### **Debug Mode**
Enable debug mode by setting:
```python
DEBUG = True
```

This will show detailed error messages in the AI responses.

## Security Considerations

### **Data Privacy**
- AI queries are sent to OpenAI's servers
- No sensitive data is stored by OpenAI
- All data is processed securely
- User context is limited to necessary information

### **Access Control**
- AI Assistant respects user permissions
- Only authenticated users can access
- User context is passed securely
- No unauthorized data access

## Performance

### **Optimization**
- Database queries are optimized
- Search results are limited to 10 items
- Context data is cached
- API calls are rate-limited

### **Monitoring**
- Monitor API usage and costs
- Track response times
- Monitor error rates
- Check user satisfaction

## Future Enhancements

### **Planned Features**
- Voice input/output
- Image recognition for assets
- Predictive analytics
- Automated reporting
- Integration with external systems

### **Advanced AI Features**
- Multi-language support
- Custom AI models
- Advanced analytics
- Machine learning insights
- Automated workflows

## Support

For issues or questions about the AI Assistant:
1. Check this guide first
2. Run the test scripts
3. Check the Django logs
4. Contact the development team

---

**Happy AI-powered asset management! 🚀**
