export default function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.status(200).json({
    status: 'online',
    platform: 'Vercel Cloud Edge',
    host_ip: 'Vercel Public',
    default_assets: {
      gameplay_count: 37,
      memes_count: 282,
      images_count: 16,
      audios_count: 12,
      green_screen_memes_count: 196,
      transparent_images_count: 7
    }
  });
}
