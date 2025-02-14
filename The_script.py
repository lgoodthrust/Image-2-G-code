import os
from PIL import Image, ImageEnhance, ImageDraw

# Prompt the user to input the directory where the image is located
image_dir = r"D:\python stuff\Image_Plotter\tester.jpg"

# Define plotter dimensions (in millimeters)
plotter_width = 110
plotter_height = 60

# Define pen down and pen up positions (in millimeters)
pen_down_position = 0  # Adjust as needed
pen_up_position = 2.5  # Adjust as needed

threshold = 220 # images threshold value (max 255)

# Define pen movement speed (in millimeters per minute)
pen_d_speed = 4500  # Adjust as needed
pen_v_speed = 12000  # Adjust as needed
pen_t_speed = 8000  # Adjust as needed

# You can adjust this value to change the contrast
contrast_factor = 2.0

# Check if the provided file exists
image_path = image_dir.strip('"')
if not os.path.isfile(image_path):
    print("Invalid file path. Please provide a valid file path.")
    exit()

# Check if the provided file is an image
if not image_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
    print("Please provide a valid image file.")
    exit()

def visualize(gcode_file_path:str, output_image_path:str):
    # Check if the G-code file exists
    if not os.path.isfile(gcode_file_path):
        print("G-code file not found. Please provide a valid file path.")
        exit()

    def gcode_l4(file_path):
        try:
            with open(file_path, 'r') as file:
                # Read the first four lines
                for i in range(4):
                    line = file.readline().strip()
                    
                # Expected format is ";data:250x250"
                if line.startswith(";data:"):
                    # Split to extract coordinates
                    data_part = line.split(":")[1]
                    x_str, y_str = data_part.split("x")
                    
                    # Convert to integers (or floats if needed)
                    x, y = int(x_str), int(y_str)
                    return (x, y)
                else:
                    raise ValueError("Line 4 does not contain the expected format ';data:<x>x<y>'")
        
        except FileNotFoundError:
            print(f"File '{file_path}' not found.")
        except ValueError as e:
            print(f"ValueError: {e}")

    background_color = (255, 255, 255)  # White background

    # Variables to track the pen state and position
    pen_is_down = False
    current_x, current_y = 0, 0
    x, y = gcode_l4(gcode_file_path)
    print(x,y)

    # Initialize image canvas
    image = Image.new("RGB", (x, y), background_color)
    draw = ImageDraw.Draw(image)

    # Parse G-code file and draw only horizontal/vertical lines
    with open(gcode_file_path, "r") as gcode_file:
        for line in gcode_file:
            # Check for pen down or up (Z movement)
            if "Z" in line:
                z_value = float(line.split("Z")[1].split()[0])
                pen_is_down = (z_value == 0)  # Assuming Z=0 is pen down

            # Check for X and Y movements
            if "X" in line and "Y" in line:
                # Extract X and Y coordinates
                x_str = line.split("X")[1].split()[0]
                y_str = line.split("Y")[1].split()[0]
                new_x = float(x_str)
                new_y = float(y_str)

                # Scale coordinates to fit the canvas
                scaled_x = int(new_x)
                scaled_y = int(new_y)

                # Only draw if the movement is purely horizontal or vertical
                if current_x == scaled_x or current_y == scaled_y:
                    if pen_is_down:
                        draw.line((current_x, current_y, scaled_x, scaled_y), fill="red", width=1)
                    #else:
                        #draw.line((current_x, current_y, scaled_x, scaled_y), fill="blue", width=1)
                #else:
                    #draw.line((current_x, current_y, scaled_x, scaled_y), fill="green", width=1)

                # Update current position
                current_x, current_y = scaled_x, scaled_y

    # Save and display the image
    image.save(output_image_path)
    image.show()

    print(f"G-code visualization saved as: {output_image_path}")

def compress_gcode(input_file:str):
    with open(input_file, 'r') as infile, open(os.path.splitext(input_file)[0] + "_smol.gcode", 'w') as outfile:
        lines = infile.readlines()
        
        # Track the last Z-coordinate and initialize an empty list to store the lines to keep
        last_z = None
        lines_to_keep = []

        for i in range(0, len(lines)):
            line = lines[i].strip()

            # Ignore comments and empty lines
            if line.startswith(';') or not line:
                lines_to_keep.append(line)
                continue

            # Extract Z movement command if it exists
            if 'G1' in line or 'G0' in line:
                # Search for the Z coordinate in the line
                parts = line.split()
                z_value = None
                for part in parts:
                    if part.startswith('Z'):
                        try:
                            z_value = float(part[1:])
                        except ValueError:
                            continue
                        break

                # If Z is modified or the line before/after a Z movement, keep the line
                if z_value is not None and z_value != last_z:
                    last_z = z_value
                    # Keep the previous line if it’s not already in the list
                    if i > 0 and lines[i - 1] not in lines_to_keep:
                        lines_to_keep.append(lines[i - 1].strip())
                    lines_to_keep.append(line)
                    # Keep the next line if it’s not already in the list
                    if i < len(lines) - 1 and lines[i + 1] not in lines_to_keep:
                        lines_to_keep.append(lines[i + 1].strip())

        # Write the compressed lines to the output file
        outfile.write('\n'.join(lines_to_keep) + '\n')

def convert_n_stuff(image_path:str):
    # Open the image and compress/resize
    image = Image.open(image_path)

    # Contrast control
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(contrast_factor)
    compressed_image = image.convert("RGB")
    compressed_image.thumbnail((1000, 1000), Image.BILINEAR)

    # Get the filename without the extension
    file_name = os.path.splitext(os.path.basename(image_path))[0]

    # Define G-code file
    gcode_file_path = f"{file_name}.gcode"
    gcode_file = open(gcode_file_path, "w")

    # G-code header
    gcode_file.write(";FLAVOR:Marlin\n")
    gcode_file.write(";TIME:120\n")
    gcode_file.write(";Filament used: 0m\n")
    gcode_file.write(";Layer height: 0.0001\n")
    gcode_file.write(";TARGET_MACHINE.NAME:Creality Ender-3 Pro\n")
    gcode_file.write("M82 ;absolute extrusion mode\n")
    gcode_file.write("G28 ; Home all axes\n")
    gcode_file.write("G1 Z5.0 F3000 ; Move Z Axis up a bit during heating to not damage bed\n")
    gcode_file.write("G1 Z2.0 F3000 ; Move Z Axis up little to prevent scratching of Heat Bed\n")
    gcode_file.write("G1 X0.1 Y20 Z0.3 F5000.0 ; Move to start position\n")

    # Convert image to grayscale for gcode
    image_gray = compressed_image.convert("L")

    # Get pixel data
    pixels = list(image_gray.getdata())

    # Save a copy of the grayscale image
    gray_image_path = f"{file_name}_gray.png"
    image_gray.save(gray_image_path)
    print(f"Grayscale image saved as: {gray_image_path}")

    # Save a copy of the black and white image
    bw_image = image_gray.point(lambda x: 0 if x < threshold else 255, 'L')
    bw_image_path = f"{file_name}_bw.png"
    bw_image.save(bw_image_path)
    print(f"Black and white image saved as: {bw_image_path}")

    # Calculate scaling factors
    scale_x = plotter_width / image_gray.width
    scale_y = plotter_height / image_gray.height

    # Define a variable to track the pen state
    pen_down = False

    # Move to the starting position
    gcode_file.write(f"G1 X10 Y10 F{pen_d_speed}\n")

    # Write G-code for each pixel in the image
    for y in range(0, image_gray.height, 2):  # Skipping every other row
        if y % 2 == 0:  # Start from left if the row number is even
            start_x = 0
            end_x = image_gray.width
            step = 1
        else:  # Start from right if the row number is odd
            start_x = image_gray.width - 1
            end_x = -1
            step = -1

        for x in range(start_x, end_x, step):
            pixel_value = pixels[y * image_gray.width + x]
            if pixel_value > threshold:  # If it's a black pixel
                if pen_down:
                    # lower the pen (start drawing)
                    gcode_file.write(f"G1 Z{pen_down_position} E0 F{pen_v_speed}\n")
                    pen_down = False
            else:  # If it's a white pixel
                if not pen_down:
                    # raise (stop drawing)
                    gcode_file.write(f"G1 Z{pen_up_position} E10 F{pen_v_speed}\n")
                    pen_down = True

            # Move to the next position with outline width factor applied
            rounded_x = round(x * scale_x, 1)
            rounded_y = round(y * scale_y, 1)
            gcode_file.write(f"G1 X{rounded_x} Y{rounded_y} E10 F{pen_d_speed}\n")

    # Raise the pen if it's still down
    if pen_down:
        gcode_file.write(f"G1 Z{pen_up_position} E0 F{pen_d_speed}\n")

    # G-code footer
    gcode_file.write("; End of G-code\n")

    # Close G-code file
    gcode_file.close()

    print(f"G-code saved as: {gcode_file_path}")

    return gcode_file_path

if __name__ == "__main__":
    gcode_file = convert_n_stuff(image_dir)
    compressed_gcode_file = compress_gcode(gcode_file)
    visualize(compressed_gcode_file)