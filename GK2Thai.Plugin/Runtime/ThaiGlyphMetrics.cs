namespace GK2Thai.Plugin.Runtime
{
    internal static class ThaiGlyphMetrics
    {
        public static float Advance(float value, int channel, float fontScale)
        { return value * 0.5f - (channel >> 4) * 0.005f * fontScale; }
    }
}
