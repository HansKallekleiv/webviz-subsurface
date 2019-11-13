from PIL import Image, ImageDraw
from selenium import webdriver
import os
import sys



def analyze(imgdir, base_img):

    screenshot_staging = Image.open(f"{imgdir}/staging/{base_img}.png")
    screenshot_production = Image.open(f"{imgdir}/{base_img}.png")
    columns = 60
    rows = 80
    screen_width, screen_height = screenshot_staging.size

    block_width = ((screen_width - 1) // columns) + 1 # this is just a division ceiling
    block_height = ((screen_height - 1) // rows) + 1

    for y in range(0, screen_height, block_height+1):
        for x in range(0, screen_width, block_width+1):
            region_staging = process_region(screenshot_staging, x, y, block_width, block_height)
            region_production = process_region(screenshot_production, x, y, block_width, block_height)

            if region_staging is not None and region_production is not None and region_production != region_staging:
                draw = ImageDraw.Draw(screenshot_staging)
                draw.rectangle((x, y, x+block_width, y+block_height), outline = "red")

    screenshot_staging.save(f"{imgdir}/diff/{base_img}.png")
    screenshot_staging.close()
    screenshot_production.close()

def process_region(image, x, y, width, height):
    region_total = 0

    # This can be used as the sensitivity factor, the larger it is the less sensitive the comparison
    factor = 100

    for coordinateY in range(y, y+height):
        for coordinateX in range(x, x+width):
            try:
                pixel = image.getpixel((coordinateX, coordinateY))
                region_total += sum(pixel)/4
            except:
                return

    return region_total/factor


