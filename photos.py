#!/usr/bin/python

from optparse import OptionParser
import sys
import os
import imghdr

# Python Image Library
import PIL
import _imaging
import Image

# pyexiv2
from pyexiv2 import metadata

import datetime

def copy_image(source, target, target_size, image_type):
  # resize image
  image = Image.open(source)
  image.thumbnail(target_size, Image.ANTIALIAS)
  image.save(target, image_type)

  # copy EXIF data
  source_image = metadata.ImageMetadata(source)
  source_image.read()
  target_image = metadata.ImageMetadata(target)
  target_image.read()
  source_image.copy(target_image)

  # set EXIF image size info to resized size
  target_image["Exif.Photo.PixelXDimension"] = image.size[0]
  target_image["Exif.Photo.PixelYDimension"] = image.size[1]
  target_image.write()

def process_directory_source_walk(options, source_dir, source_filenames):
  for source_filename in source_filenames:

    # Make some checks to see this is a supported file
    source_path = os.path.join(source_dir, source_filename)
    if os.path.isdir(source_path): 
      continue
    if not os.path.isfile(source_path): 
      continue
    try:
      image_type = imghdr.what(source_path)
    except:
      continue
    if image_type is None or image_type not in ['jpeg', 'png']:
      continue

    source_relpath = os.path.relpath(source_path, options.directory_source)

    (source_reldir,none) = os.path.split(source_relpath)

    for target_size in options.target_sizes:
      target_reldir = os.path.join(target_size['directory'], source_reldir)

      target_dir = os.path.join(options.directory_target, target_reldir)
      target_path = os.path.join(target_dir, source_filename)

      if os.path.exists(target_path) and os.path.getmtime(source_path) <= os.path.getmtime(target_path):
        continue

      # Make sure the target directory exists
      if not os.path.exists(target_dir):
        os.makedirs(target_dir)

      try:
        copy_image(source_path, target_path, (target_size['width'], target_size['height']), image_type)
      except:
        print source_path
        continue

def process_directory_target_walk(args, target_dir, target_filenames):
  (options, target_size) = args

  for target_filename in target_filenames:

    # Make sure this is a file
    target_path = os.path.join(target_dir, target_filename)
    if not os.path.isfile(target_path): 
      continue

    source_relpath = os.path.relpath(target_path, os.path.join(options.directory_target, target_size['directory']))
    
    # Remove the file if it is removed from the source directory
    if not os.path.exists(os.path.join(options.directory_source, source_relpath)):
      if options.no_delete:
        print 'would remove file ', target_path
      else:
        os.remove(target_path)

  # Remove directory if empty
  if not os.listdir(target_dir):
    if options.no_delete:
      print 'would remove directory ', target_dir
    else:
      os.rmdir(target_dir)

def main(argv=None):
  if argv is None:
    argv = sys.argv

  parser = OptionParser()
  parser.add_option("-s", "--directory-source", dest="directory_source",
                    help="Manage originals in this directory", metavar="PATH")
  parser.add_option("-t", "--directory-target", dest="directory_target",
                    help="Directory where copies will be stored", metavar="PATH")
  parser.add_option("--working-directory", dest="working_directory",
                    help="This will be the working directory with copies [NOT YET IMPLEMENTED]", metavar="WIDTHxHEIGHT[:DIRECTORY]")
  parser.add_option("--add-target-size", dest="target_sizes", action="append",
                    help="Add a size to generate", metavar="WIDTHxHEIGHT[:DIRECTORY]")
  parser.add_option("--add-subdirectory", dest="subdirectories", action="append",
                    help="Limit to provided subdirectories", metavar="SUBPATH")
  parser.add_option("--no-delete", action="store_true", dest="no_delete", default=False,
                    help="Print what would be removed instead of removing")

  (options, args) = parser.parse_args()

  # Check required arguments
  if options.directory_source is None:
    sys.exit("--directory-source is required")
  if options.directory_target is None:
    sys.exit("--directory-target is required")

  # Add a default target size if none is provided
  if options.target_sizes is None:
    options.target_sizes = [{'width': 1600, 'height': 1200, 'directory': '1600x1200'}]
  # Or parse the
  else:
    i = 0;
    for target_size in options.target_sizes[:]:
      try:
        (size, directory) = target_size.split(':')
      except:
        directory = size = target_size
      if len(directory) == 0:
        sys.exit("--add-target-size argument %s is not a valid target size" % target_size)
      try:
        (width, height) = size.split('x')
        width = int(width)
        height = int(height)
      except:
        sys.exit("--add-target-size argument %s is not a valid target size" % target_size)
      options.target_sizes[i] = {'width': width, 'height': height, 'directory': directory}
      i += 1

  if options.working_directory:
    try:
      (size, directory) = options.working_directory.split(':')
    except:
      directory = size = options.working_directory
    if len(directory) == 0:
      sys.exit("--working-directory argument %s is not valid" % options.working_directory)
    try:
      (width, height) = size.split('x')
      width = int(width)
      height = int(height)
    except:
      sys.exit("--working-directory argument %s is not valid" % options.working_directory)
    options.working_directory = {'width': width, 'height': height, 'directory': directory}

  if options.subdirectories:
    for (i, subdirectory) in enumerate(options.subdirectories):
      if subdirectory == '-YEAR-':
        now = datetime.datetime.now()
        options.subdirectories[i] = str(now.year)

  # Evaluate originals and copies directories
  options.directory_source = os.path.realpath(options.directory_source)
  options.directory_target = os.path.realpath(options.directory_target)

  if not os.path.isdir(options.directory_source):
    sys.exit("--directory-source is not a valid directory")

  if not os.path.isdir(options.directory_target):
    sys.exit("--directory-target is not a valid directory")

  if os.path.commonprefix([options.directory_source, options.directory_target]) == options.directory_source:
    sys.exit("--directory-target can not be a directory inside --directory-source")

  if options.subdirectories:
    for subdirectory in options.subdirectories:
      os.path.walk(unicode(os.path.join(options.directory_source, subdirectory)), process_directory_source_walk, options)
      for target_size in options.target_sizes:
        os.path.walk(os.path.join(options.directory_target, target_size['directory'], subdirectory), process_directory_target_walk, [options, target_size])
  else:
    os.path.walk(unicode(options.directory_source), process_directory_source_walk, options)
    for target_size in options.target_sizes:
      os.path.walk(os.path.join(options.directory_target, target_size['directory']), process_directory_target_walk, [options, target_size])
    

if __name__ == "__main__":
  main();

