import os
from PIL import Image, ImageEnhance, ImageDraw

# Image and plotter settings
image_dir = r"D:\python stuff\Image_Plotter\gradient.png"
plotter_width, plotter_height = 1000, 1000
pen_down_position, pen_up_position = 0, 2.5
threshold = 128  # max of 255
pen_d_speed, pen_v_speed, pen_t_speed = 4500, 12000, 8000
contrast_factor = 1.0
invert_drawing = True   # Toggle inversion mode

# Ensure script has write permissions in the working directory
path = os.path.dirname(image_dir)  # Get directory instead of stripping file extension
if os.path.isdir(path):  
    os.chdir(path)
    print(f"Current working directory: {os.getcwd()}")
else:
    print(f"Warning: Directory {path} does not exist.")

def to_gray(image_path):
    """ Converts an image into a grayscale. """
    print(f"Opening image: {image_path}")
    image = Image.open(image_path)
    image = image.convert("RGB", None, None, None, 128) # simplify colors
    image = image.convert("L") # grayscale
    enhancer = ImageEnhance.Contrast(image) # contrast thiggy

    # Save processed images
    file_name = os.path.splitext(os.path.basename(image_path))[0]
    gray_image_path = os.path.join(os.getcwd(), f"{file_name}_gray.png")
    print(f"Saving grayscale image at: {gray_image_path}")
    enhancer.enhance(contrast_factor).save(gray_image_path)
    return gray_image_path

def to_bl(image_path):
    """ Converts a grayscale image into B&W. """
    file_name = os.path.splitext(os.path.basename(image_path))[0]
    image_gray = Image.open(image_path)
    bw_image = image_gray.point(lambda x: 0 if x < threshold else 255, 'L')
    bw_image_path = os.path.join(os.getcwd(), f"{file_name}_bw.png")
    print(f"Saving black-and-white image at: {bw_image_path}")
    bw_image.save(bw_image_path)
    return bw_image_path

def to_db(image_path):
    """Generates a boundary-detected image where pixels are black only if there is a black-to-white transition horizontally."""
    file_name = os.path.splitext(os.path.basename(image_path))[0]
    bw_image = Image.open(image_path)
    width, height = bw_image.size
    bd_image = Image.new("L", (width, height), 255)  # Start with a white image
    pixels_bw = bw_image.load()
    pixels_bd = bd_image.load()

    for y in range(height):
        for x in range(width - 1):  # Horizontal scan
            if pixels_bw[x, y] == 0 and pixels_bw[x + 1, y] == 255:  # Black to white transition
                pixels_bd[x, y] = 0  # Mark transition pixel as black
    
    bd_image_path = os.path.join(os.getcwd(), f"{file_name}_bd.png")
    bd_image.save(bd_image_path)
    return bd_image_path

def to_gcode(image_path):
    # Resize while keeping aspect ratio
    image = Image.open(image_path)
    image.thumbnail((plotter_width, plotter_height), Image.Resampling.BILINEAR, 2.0)
    compressed_width, compressed_height = image.size
    scale_factor = min(plotter_width / compressed_width, plotter_height / compressed_height)
    file_name = os.path.splitext(os.path.basename(image_path))[0]

    # Create G-code file
    gcode_file_path = os.path.join(os.getcwd(), f"{file_name}.gcode")
    print(f"Saving G-code at: {gcode_file_path}")

    try:
        print(f"Attempting to write G-code to {gcode_file_path}...")
        with open(gcode_file_path, "w") as gcode_file:
            print("File opened successfully, writing G-code...")
            gcode_file.write(";FLAVOR:Marlin\nG28 ; Home all axes\nG1 Z5.0 F3000\nG1 Z2.0 F3000\nG1 X0.1 Y20 Z0.3 F5000.0\n")
            
            pixels = list(image.getdata())
            pen_down = False

            for y in range(image.height):
                x_range = range(image.width) if y % 2 == 0 else range(image.width - 1, -1, -1)
                for x in x_range:
                    pixel_value = pixels[y * image.width + x]
                    draw_condition = pixel_value >= threshold if invert_drawing else pixel_value <= threshold

                    if draw_condition:
                        if not pen_down:
                            gcode_file.write(f"G1 Z{pen_down_position} F{pen_v_speed}\n")
                            pen_down = True
                    else:
                        if pen_down:
                            gcode_file.write(f"G1 Z{pen_up_position} F{pen_v_speed}\n")
                            pen_down = False
                    
                    gcode_file.write(f"G1 X{round(x * scale_factor, 2)} Y{round(y * scale_factor, 2)} F{pen_d_speed}\n")
            
            if pen_down:
                gcode_file.write(f"G1 Z{pen_up_position} F{pen_d_speed}\n")
            gcode_file.write("; End of G-code\n")

        print(f"G-code successfully saved as: {gcode_file_path}")
    except Exception as e:
        print(f"Error saving G-code file: {e}")
    
    return gcode_file_path

def compress_gcode(input_file):
    """ Optimizes G-code by removing redundant movement commands. """
    optimized_file_path = os.path.splitext(input_file)[0] + "_optimized.gcode"
    last_x, last_y, last_z = None, None, None

    with open(input_file, 'r') as infile, open(optimized_file_path, 'w') as outfile:
        for line in infile:
            line = line.strip()
            if line.startswith(';') or not line:
                outfile.write(line + '\n')
                continue

            x_value = next((float(part[1:]) for part in line.split() if part.startswith('X')), None)
            y_value = next((float(part[1:]) for part in line.split() if part.startswith('Y')), None)
            z_value = next((float(part[1:]) for part in line.split() if part.startswith('Z')), None)

            if x_value == last_x and y_value == last_y and z_value == last_z:
                continue

            if z_value is not None:
                last_z = z_value
            if x_value is not None:
                last_x = x_value
            if y_value is not None:
                last_y = y_value

            outfile.write(line + '\n')

    print(f"G-code Optimization saved as: {optimized_file_path}")
    return optimized_file_path

def visualize(gcode_file_path):
    """ Reads a G-code file and visualizes it as an image. """
    print(f"Opening G-code for visualization: {gcode_file_path}")
    image = Image.new("RGB", (plotter_width, plotter_height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    pen_is_down = False
    last_x, last_y = None, None

    with open(gcode_file_path, "r") as gcode_file:
        for line in gcode_file:
            if "Z" in line:
                z_value = float(line.split("Z")[1].split()[0])
                pen_is_down = (z_value == pen_down_position)

            if "X" in line and "Y" in line:
                x_value = float(next(part[1:] for part in line.split() if part.startswith('X')))
                y_value = float(next(part[1:] for part in line.split() if part.startswith('Y')))
                
                if last_x is not None and last_y is not None and pen_is_down:
                    draw.line((last_x, last_y, x_value, y_value), fill="red", width=1)

                last_x, last_y = x_value, y_value

    output_image_path = f"{os.path.splitext(os.path.basename(gcode_file_path))[0]}_visualization.png"
    print(f"Saving visualization at: {output_image_path}")
    image.save(output_image_path)
    image.show()

A = to_gray(image_dir)
B = to_bl(A)
C = B # C = to_db(B)
D = to_gcode(C)
E = compress_gcode(D)
visualize(E)
