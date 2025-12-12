# Certificate Templates

Place your custom certificate template PNG file here.

## Template Requirements

- **Filename**: `template.png` (or specify a custom name)
- **Recommended Size**: 1920 x 1080 pixels (landscape)
- **Format**: PNG with transparency support

## Text Overlay Positions

The certificate generator will overlay the following text on your template:

| Element | Position (% from top) | Font Size | Color |
|---------|----------------------|-----------|-------|
| "CERTIFICATE OF COMPLETION" | 22% | 3.5% of height | #e94560 |
| "This is to certify that" | 32% | 2.2% of height | #888888 |
| **Student Name** | 40% | 6.5% of height | #ffffff |
| "has successfully completed" | 48% | 2.2% of height | #888888 |
| **Course Title** | 56% | 4.5% of height | #e94560 |
| Attendance Info | 65% | 2% of height | #aaaaaa |
| Instructor Name | 78% (left) | 2.2% of height | #ffffff |
| Issue Date | 78% (center) | 2.2% of height | #ffffff |
| Certificate Code | 78% (right) | 2.2% of height | #e94560 |

## Design Tips

1. Leave the center area (20-70% from top) relatively clear for text overlays
2. Use a dark background for better text visibility
3. Add decorative borders and corners
4. Include your logo at the top
5. Keep important design elements at the edges

## Default Template

If no `template.png` is found, the system will generate a default dark-themed certificate with decorative borders and gradient background.

## Custom Fonts

To use custom fonts, place TTF files in `/static/fonts/`:
- `Poppins-Regular.ttf`
- `Poppins-Bold.ttf`

The system will fall back to system fonts if custom fonts aren't available.
