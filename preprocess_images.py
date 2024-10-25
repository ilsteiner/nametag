from PIL import Image, ImageOps, ImageFilter
import os
import sys

def batch_process_icons(input_folder):
    output_folder = os.path.join(input_folder, 'output')

    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    for filename in os.listdir(input_folder):
        if filename.endswith(".png"):
            # Open the image
            img_path = os.path.join(input_folder, filename)
            img = Image.open(img_path).convert("RGBA")

            # Create an outline by expanding and filling the alpha channel
            outline = ImageOps.expand(img, border=3, fill='black')

            # Add drop shadow
            shadow = outline.copy()
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=2))

            # Crop the shadow to match the original image size
            shadow = shadow.crop((3, 3, img.width + 3, img.height + 3))

            # Combine shadow and original image
            combined = Image.alpha_composite(shadow, img)

            # Save the modified image
            output_path = os.path.join(output_folder, filename)
            combined.save(output_path, 'PNG')

    print("Batch processing complete!")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <input_directory>")
        sys.exit(1)

    input_directory = sys.argv[1]
    batch_process_icons(input_directory)
