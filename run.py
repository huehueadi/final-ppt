from PIL import Image

def generate_diagonal_gradient(start_color, end_color, size=(1920, 1080), output_path="gradient_slide.png"):
    width, height = size
    image = Image.new("RGB", size)
    pixels = image.load()

    for y in range(height):
        for x in range(width):
            # Calculate the interpolation factor based on diagonal position
            t = (x + y) / (width + height)
            r = int(start_color[0] * (1 - t) + end_color[0] * t)
            g = int(start_color[1] * (1 - t) + end_color[1] * t)
            b = int(start_color[2] * (1 - t) + end_color[2] * t)
            pixels[x, y] = (r, g, b)

    image.save(output_path)
    print(f"Gradient slide saved as: {output_path}")

# Example usage
start_rgb = (255, 94, 98)  # Orange-red
end_rgb = (255, 195, 113)    # Blue-purple
generate_diagonal_gradient(start_rgb, end_rgb)
