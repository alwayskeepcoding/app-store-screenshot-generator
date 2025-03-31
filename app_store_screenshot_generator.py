#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
App Store Screenshot Generator
==============================

This script creates app store-style screenshots by placing framed device mockups
containing your app screenshots onto a background image using relative positioning
and sizing.

See README.md for usage instructions.
"""
from PIL import Image, ImageDraw
import os
from typing import List, Dict, Tuple, Union, Optional

# Create output directory
output_dir = "output"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# --- Default Values ---
# Defaults (Relative to Device Width)
DEFAULT_RELATIVE_BORDER_WIDTH = 0.02  # e.g., 2% of device width
DEFAULT_RELATIVE_CORNER_RADIUS = 0.2  # e.g., 20% of device width

# --- Helper Function: Create Device Frame ---
def create_device_frame(width: int, height: int, content_width: int, content_height: int,
                        border_width: int, corner_radius: int) -> Image.Image:
    """
    Creates a device frame image with a transparent content area using absolute pixel values.
    NOTE: This function REQUIRES absolute border_width and corner_radius to be passed.
          Defaults are handled in the calling function (create_app_store_screenshot).

    Args:
        width: The total width of the frame in pixels.
        height: The total height of the frame in pixels.
        content_width: The width of the transparent content area in pixels.
        content_height: The height of the transparent content area in pixels.
        border_width: The width of the frame border in pixels (absolute).
        corner_radius: The radius of the outer corners of the frame in pixels (absolute).

    Returns:
        A PIL Image object representing the device frame.
    """
    # Create transparent background for the frame
    frame = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)

    # Calculate content area position (centered) - absolute within the frame
    content_x = (width - content_width) // 2
    content_y = (height - content_height) // 2

    # Ensure border width doesn't exceed half the minimum dimension or radius
    effective_border_width = min(border_width, width // 2, height // 2, corner_radius)
    if effective_border_width < 0: effective_border_width = 0 # Cannot be negative

    # Draw outer rounded rectangle (the frame itself) - Black frame
    outer_rect = [(0, 0), (width -1, height -1)] # Use -1 to avoid potential drawing overflow
    draw.rounded_rectangle(outer_rect, radius=corner_radius, fill=(0, 0, 0, 255))

    # Draw inner rounded rectangle (transparent content area)
    inner_corner_radius = max(0, corner_radius - effective_border_width)
    inner_rect = [(content_x, content_y), (content_x + content_width -1, content_y + content_height -1)] # -1 for inner rect too
    # Use transparent fill to punch a hole
    draw.rounded_rectangle(inner_rect, radius=inner_corner_radius, fill=(0, 0, 0, 0))

    return frame

# --- Core Screenshot Generation Function ---
def create_app_store_screenshot(background_image: Union[str, Image.Image],
                                screenshots_config: List[Dict],
                                output_path: Optional[str] = None) -> Optional[Image.Image]:
    """
    Creates an app store screenshot by placing one or more app screenshots
    with device frames onto a background image, using relative positioning and sizing.
    Border and corner radius are also relative by default.

    Args:
        background_image: Path to the background image file or a PIL Image object.
        screenshots_config: A list of dictionaries, each configuring a screenshot to add.
            Each dict should contain:
            - 'image': Path to the screenshot file or a PIL Image object. (Required)
            - 'relative_width': Float representing the desired device frame width as a
                                fraction of the background image width (e.g., 0.8 for 80%). (Required)
            - 'relative_position': Tuple (rel_x, rel_y) for the *center* of the device frame
                                   relative to the background dimensions (e.g., (0.5, 0.5) for center). (Required)
            - 'relative_border_width': Float, border width as a fraction of device width.
                                       (Optional, defaults to DEFAULT_RELATIVE_BORDER_WIDTH)
            - 'relative_corner_radius': Float, corner radius as a fraction of device width.
                                        (Optional, defaults to DEFAULT_RELATIVE_CORNER_RADIUS)
            - 'z_order': Integer for stacking order (higher value is on top). (Optional, defaults to 0)
        output_path: Path to save the final screenshot image. If None, the function
                     returns the final PIL Image object instead of saving.

    Returns:
        The final PIL Image object if output_path is None, otherwise None. Returns None on fatal errors.
    """
    # Load background image
    if isinstance(background_image, str):
        try:
            bg = Image.open(background_image).convert("RGBA")
        except FileNotFoundError:
            print(f"Error: Background image not found at {background_image}")
            return None
    elif isinstance(background_image, Image.Image):
        bg = background_image.copy().convert("RGBA")
    else:
        print("Error: Invalid background_image type. Must be path string or PIL Image.")
        return None

    bg_width, bg_height = bg.size
    final_image = bg # Start with the background

    # Sort screenshots by z_order if provided, lower z_order drawn first
    screenshots_config_sorted = sorted(
        screenshots_config,
        key=lambda cfg: cfg.get('z_order', 0) # Default z_order is 0
    )

    for config in screenshots_config_sorted:
        # --- Get configuration for this screenshot ---
        screenshot_source = config.get('image')
        rel_width_factor = config.get('relative_width')
        rel_center_pos = config.get('relative_position')
        # Get RELATIVE border/radius, using defaults if not provided
        rel_border_width = config.get('relative_border_width', DEFAULT_RELATIVE_BORDER_WIDTH)
        rel_corner_radius = config.get('relative_corner_radius', DEFAULT_RELATIVE_CORNER_RADIUS)

        # --- Validate required parameters ---
        if not screenshot_source:
            print("Warning: Skipping screenshot config due to missing 'image'.")
            continue
        if rel_width_factor is None:
            print(f"Warning: Skipping screenshot config due to missing 'relative_width'. Config: {config}")
            continue
        if rel_center_pos is None or not isinstance(rel_center_pos, tuple) or len(rel_center_pos) != 2:
            print(f"Warning: Skipping screenshot config due to missing or invalid 'relative_position'. Expected (rel_x, rel_y). Config: {config}")
            continue
        try:
            # Validate relative factors
            rel_width_factor = float(rel_width_factor)
            rel_center_x = float(rel_center_pos[0])
            rel_center_y = float(rel_center_pos[1])
            rel_border_width = float(rel_border_width)
            rel_corner_radius = float(rel_corner_radius)
            if not (0.0 < rel_width_factor <= 1.5): # Allow slightly > 1 for effect, but warn
                 if rel_width_factor > 1.0:
                    print(f"Warning: 'relative_width' ({rel_width_factor}) > 1.0. Device will be wider than background.")
                 elif rel_width_factor <= 0:
                     print(f"Error: 'relative_width' ({rel_width_factor}) must be positive. Skipping config: {config}")
                     continue
            if not (0.0 <= rel_border_width < 0.5): # Border can't be >= half the width
                 print(f"Warning: 'relative_border_width' ({rel_border_width}) seems high or negative. Should be >= 0.0 and < 0.5. Clamping or check config.")
                 rel_border_width = max(0.0, min(rel_border_width, 0.49))
            if not (0.0 <= rel_corner_radius):
                 print(f"Warning: 'relative_corner_radius' ({rel_corner_radius}) cannot be negative. Setting to 0.")
                 rel_corner_radius = 0.0
        except (ValueError, TypeError) as e:
             print(f"Warning: Invalid value in relative sizing/positioning parameters: {e}. Skipping config: {config}")
             continue

        # --- Load screenshot to get aspect ratio ---
        if isinstance(screenshot_source, str):
            try:
                screenshot_img = Image.open(screenshot_source).convert("RGBA")
            except FileNotFoundError:
                print(f"Warning: Screenshot image not found at {screenshot_source}. Skipping.")
                continue
            except Exception as e:
                print(f"Warning: Could not open screenshot image {screenshot_source}: {e}. Skipping.")
                continue
        elif isinstance(screenshot_source, Image.Image):
            screenshot_img = screenshot_source.copy().convert("RGBA")
        else:
            print("Warning: Invalid screenshot 'image' type. Skipping.")
            continue

        ss_width, ss_height = screenshot_img.size
        if ss_width <= 0 or ss_height <= 0:
            print(f"Warning: Screenshot '{screenshot_source}' has invalid dimensions ({ss_width}x{ss_height}). Skipping.")
            continue
        aspect_ratio = ss_height / ss_width

        # --- Calculate Absolute Dimensions based on relative factors ---
        # Calculate device frame width
        dev_width = int(bg_width * rel_width_factor)
        if dev_width <= 0:
            print(f"Warning: Calculated device width ({dev_width}) is zero or negative. Check 'relative_width'. Skipping.")
            continue

        # --- Calculate ABSOLUTE border width and corner radius ---
        border_width_abs = max(0, int(dev_width * rel_border_width))
        corner_radius_abs = max(0, int(dev_width * rel_corner_radius))

        # Ensure calculated absolute border width isn't too large for the device size
        safe_border_width = min(border_width_abs, dev_width // 2 -1, corner_radius_abs) # Subtract 1 for safety margin, Check against corner radius
        if safe_border_width < 0 : safe_border_width = 0

        # Calculate content dimensions maintaining aspect ratio
        content_width = dev_width - 2 * safe_border_width
        if content_width <= 0:
             print(f"Warning: Calculated content width ({content_width}) is zero or negative "
                   f"for device width ({dev_width}) and effective border width ({safe_border_width}). Check relative params. Skipping.")
             continue

        content_height = int(content_width * aspect_ratio)
        if content_height <= 0:
             print(f"Warning: Calculated content height ({content_height}) is zero or negative. "
                   f"Check screenshot aspect ratio or calculated content width. Skipping.")
             continue

        # Calculate device frame height based on content height
        dev_height = content_height + 2 * safe_border_width
        if dev_height <= 0:
             print(f"Warning: Calculated device height ({dev_height}) is zero or negative. Skipping.")
             continue

        # Recalculate safe border width now that we have dev_height
        final_safe_border_width = min(border_width_abs, dev_width // 2 -1, dev_height // 2 -1, corner_radius_abs)
        if final_safe_border_width < 0: final_safe_border_width = 0
        # Update content dims if border width changed
        content_width = dev_width - 2 * final_safe_border_width
        content_height = int(content_width * aspect_ratio)
        if content_width <= 0 or content_height <= 0:
             print(f"Warning: Final content dimensions negative/zero after safety checks. Skipping.")
             continue
        dev_height = content_height + 2 * final_safe_border_width # Recalc final dev height


        # Calculate absolute top-left position based on relative center
        center_x_abs = int(bg_width * rel_center_x)
        center_y_abs = int(bg_height * rel_center_y)
        pos_x = center_x_abs - dev_width // 2
        pos_y = center_y_abs - dev_height // 2

        # --- Resize screenshot ---
        try:
            # Use LANCZOS for high quality resize
            screenshot_resized = screenshot_img.resize((content_width, content_height), Image.Resampling.LANCZOS)
        except ValueError as e:
            print(f"Error resizing screenshot to {content_width}x{content_height}: {e}. Skipping.")
            continue
        except Exception as e:
             print(f"Unexpected error resizing screenshot: {e}. Skipping.")
             continue


        # --- Create mask for rounded corners on the screenshot content ---
        # Content corner radius should be inner radius of the frame
        content_corner_radius = max(0, corner_radius_abs - final_safe_border_width)
        mask = Image.new("L", (content_width, content_height), 0) # Mask is grayscale
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([(0, 0), (content_width, content_height)],
                                    radius=content_corner_radius, fill=255) # White=Keep

        # Apply alpha mask to the resized screenshot itself for correct pasting
        # Create a temporary RGBA image to apply the mask correctly
        temp_img = Image.new("RGBA", (content_width, content_height))
        temp_img.paste(screenshot_resized, (0,0))
        temp_img.putalpha(mask) # Apply the grayscale mask to the alpha channel

        # --- Create the device frame ---
        device_frame = create_device_frame(dev_width, dev_height, content_width, content_height,
                                           final_safe_border_width, corner_radius_abs) # Pass calculated absolutes

        # --- Paste screenshot content onto the final image ---
        # Content paste position is the frame's top-left + border width
        content_paste_pos = (pos_x + final_safe_border_width, pos_y + final_safe_border_width)

        # Paste using the mask we created (temp_img already has it in alpha)
        final_image.paste(temp_img, content_paste_pos, temp_img)

        # --- Paste device frame onto the final image ---
        # Frame paste position is the calculated top-left
        final_image.paste(device_frame, (pos_x, pos_y), device_frame) # Use frame's alpha

    # --- Output ---
    if output_path:
        try:
            # Ensure output directory exists if path includes directories
            output_dir_for_file = os.path.dirname(output_path)
            if output_dir_for_file and not os.path.exists(output_dir_for_file):
                os.makedirs(output_dir_for_file)
            final_image.save(output_path)
            # print(f"Screenshot saved to: {output_path}") # Keep console less verbose for multiple runs
            return None # Indicate success by returning None when saving
        except Exception as e:
            print(f"Error saving image to {output_path}: {e}")
            return final_image # Return image even if save failed
    else:
        return final_image # Return the image object if no path provided

# --- Main Execution Logic (Example Usage) ---
if __name__ == "__main__":
    print("Starting App Store Screenshot generation...")

    # --- Define Example Files (User should place these in the same directory as the script) ---
    EXAMPLE_BACKGROUND = "background.jpeg" # Provide a background image
    EXAMPLE_SCREENSHOT_1 = "screenshot1.png" # Provide screenshot 1
    EXAMPLE_SCREENSHOT_2 = "screenshot2.png" # Provide screenshot 2
    EXAMPLE_SCREENSHOT_3 = "screenshot3.png" # Provide screenshot 3

    # List of required example files
    required_files = [EXAMPLE_BACKGROUND, EXAMPLE_SCREENSHOT_1, EXAMPLE_SCREENSHOT_2, EXAMPLE_SCREENSHOT_3]
    missing_files = [f for f in required_files if not os.path.exists(f)]

    if missing_files:
        print("\n--- ERROR ---")
        print("Missing required example image files:")
        for f in missing_files:
            print(f"- {f}")
        print("Please place these files in the same directory as the script to run the examples.")
        print("-------------\n")
        exit(1) # Exit if example files aren't present

    # --- Example Configurations ---
    EXAMPLE_DEFINITIONS = {
        "example_1_single": {
            "background": EXAMPLE_BACKGROUND,
            "config": [
                {
                    "image": EXAMPLE_SCREENSHOT_1,
                    "relative_width": 0.83,
                    "relative_position": (0.5, 0.57),
                    "z_order": 0
                }
            ],
            "output": os.path.join(output_dir, "example_1_single.png")
        },
        "example_2_double": {
            "background": EXAMPLE_BACKGROUND,
            "config": [
                {
                    "image": EXAMPLE_SCREENSHOT_1,
                    "relative_width": 0.45,
                    "relative_position": (0.25, 0.4),
                    "z_order": 0
                },
                {
                    "image": EXAMPLE_SCREENSHOT_2,
                    "relative_width": 0.45,
                    "relative_position": (0.75, 0.4),
                    "z_order": 1
                }
            ],
            "output": os.path.join(output_dir, "example_2_double.png")
        },
        "example_3_triple_overlap": {
            "background": EXAMPLE_BACKGROUND,
            "config": [
                # Layer 1 (Bottom)
                {
                    "image": EXAMPLE_SCREENSHOT_1,
                    "relative_width": 0.54,
                    "relative_position": (0.34, 0.47),
                    "z_order": 0
                },
                # Layer 2 (Middle)
                {
                    "image": EXAMPLE_SCREENSHOT_2,
                    "relative_width": 0.54,
                    "relative_position": (0.5, 0.55),
                    "z_order": 1
                },
                # Layer 3 (Top)
                {
                    "image": EXAMPLE_SCREENSHOT_3,
                    "relative_width": 0.54,
                    "relative_position": (0.66, 0.63),
                    "z_order": 2
                },
            ],
             "output": os.path.join(output_dir, "example_3_triple_overlap.png")
         }
    }

    processed_count = 0
    failed_count = 0

    for name, definition in EXAMPLE_DEFINITIONS.items():
        print(f"Generating: {name} -> {definition['output']}")
        result = create_app_store_screenshot(
            background_image=definition["background"],
            screenshots_config=definition["config"],
            output_path=definition["output"]
        )

        # create_app_store_screenshot returns None on success when output_path is set
        if result is None and os.path.exists(definition['output']):
            processed_count += 1
        else:
            failed_count += 1
            print(f"Error encountered during processing or saving for {name}.")
            if result is not None:
                 print("Function returned an image object, check saving permissions or path.")

    print("\n--- App Store Screenshot Generation Summary ---")
    print(f"Successfully generated: {processed_count}")
    print(f"Failed examples:        {failed_count}")
    if processed_count > 0:
        print(f"Generated examples are in the '{output_dir}' directory.")
    if failed_count > 0:
         print("Please check warnings or errors above for details.")
    print("---------------------------------------------")