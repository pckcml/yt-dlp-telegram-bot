Simple YTDL Telegram bot.

This was made reusing most of the code found on Thorbijoern/yt-dl_bot and zaini/yt-dl-chatbot (both at GitHub). I wanted this to work with yt-dlp instead of the tools they used, though.

To use this bot, all you need to do is edit settings.json to include your bot token and the whitelisted users, and the path to the yt-dlp binary and your download location on your server. This should be combined with a good cron job to clean the download directory, if you don't want to hoard the downloaded stuff. Then you can run main.py.

Overall this was a learning project, as I didn't really dig much deeper around the internet to see if anyone had made something like this, but better. But if this works for someone, I'll be happy.

I intend to work on it to make a few things better, though. This is the first working version so far and I'm not an expert developer, so things might take a while to happen.