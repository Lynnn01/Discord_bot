from functools import wraps
import logging
from typing import Callable, Any
import discord

logger = logging.getLogger(__name__)

def dev_command_error_handler():
    """Decorator สำหรับจัดการ error ใน dev commands"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args: Any, **kwargs: Any):
            try:
                return await func(self, interaction, *args, **kwargs)
            except Exception as e:
                # Log error
                logger.error(f"Error in dev command {func.__name__}: {str(e)}")
                
                # Update command history
                if hasattr(self, '_history'):
                    action = kwargs.get('action', func.__name__)
                    self._history.add(interaction.user, action, False)
                
                # Send error message
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            f"❌ เกิดข้อผิดพลาด: {str(e)}", 
                            ephemeral=True
                        )
                    else:
                        await interaction.followup.send(
                            f"❌ เกิดข้อผิดพลาด: {str(e)}", 
                            ephemeral=True
                        )
                except Exception as send_error:
                    logger.error(f"Error sending error message: {str(send_error)}")
                    
        return wrapper
    return decorator
