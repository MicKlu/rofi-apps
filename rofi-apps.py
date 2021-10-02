#!/usr/bin/env python3

from gi.repository import Gio
import json
import locale
from pathlib import Path
import re
import sys

CONFIG_PATHS = {
	"relative": Path(__file__).parent.absolute() / "config",
	"global": Path("/usr/share/rofi-apps/config"),
	"user": Path.home() / ".config/rofi-apps/config"
}

ENTRIES_PATHS = [
	Path.home() / ".local/share/applications",
	Path("/usr/local/share/applications"),
	Path("/usr/share/applications")
]

def main():
	
	if CONFIG_PATHS["user"].exists():
		config = Config(CONFIG_PATHS["user"])
	elif CONFIG_PATHS["global"].exists():
		config = Config(CONFIG_PATHS["global"])
	elif CONFIG_PATHS["relative"].exists():
		config = Config(CONFIG_PATHS["relative"])
	else:
		print(f"[!] Config not found.", file=sys.stderr)
		sys.exit(1)

	# Lists for storing entries
	entriesPinned = []
	entriesSorted = []

	for entriesPaths in ENTRIES_PATHS:
		for entryPath in entriesPaths.rglob("*"):
			# Skip directories
			if entryPath.is_dir():
				continue

			try:
				entry = Entry(str(entryPath))

				# Ignore hidden entries (NoDisplay=true)
				if entry.getNoDisplay():
					continue;

				# Ignore blacklisted entries
				if entry.isBlacklisted(config):
					continue

				# Ignore duplicated entries
				if entry.getFilename() in [e.getFilename() for e in entriesPinned + entriesSorted]:
					continue

				entriesSorted.append(entry)

			except TypeError as e:
				# Normally not a desktop entry, but print error anyway
				print(f"[@] TypeError while processing {entryPath}. Probably not a desktop entry.", file=sys.stderr)
				print(f"[@] {e}", file=sys.stderr)

	# Sort ordered list
	locale.setlocale(locale.LC_ALL, '')
	entriesSorted.sort(key=lambda entry: locale.strxfrm(entry.getName()))

	# Concatenate lists
	entries = entriesPinned + entriesSorted

	# Display final entries
	for entry in entries:
		if entry:
			# print(f"{entry.getName()}\0icon\x1f{item['icon']}\x1finfo\x1f{item['executable']}")
			print(f"{entry.getName()}\0icon\x1f{entry.getIcon()}\x1finfo\x1f{entry.getPath()}")


class Config:
	"""
	Reads config file and does matching for custom entries

	Attributes:
		blacklist - list of blacklist rules
		pinned - list of pinned rules
		rename - list of custom name rules

	Methods:
		getBlacklist() - Returns list of blacklisted entries rules
		getPinned() - Returns list of pinned entries rules
		getCustoms() - Returns list of custom entries rules and values
	"""

	def __init__(self, path):
		"""
		Open config file and extract blacklist and pinned rules
		"""

		with open(path, "r") as f:
			configJson = f.read()
			configJson = re.sub("//.*?$", "", configJson, flags=re.M)
			config = json.loads(configJson)
			self.blacklist = config["blacklist"]
			self.pinned = config["pinned"]
			self.customs = config["customs"]

	def getBlacklist(self):
		return self.blacklist

	def getPinned(self):
		return self.pinned

	def getCustoms(self):
		return self.customs

class Entry():
	"""
	Wrapper class for Gio.DesktopAppInfo object. Includes additional
	methods for filtering entries.

	Attributes:
		entry - Gio.DesktopAppInfo object containing actual entry data
		customName - custom name for entry set by user

	Methods:
		isBlacklisted(config) - Check if desktop entry is blacklisted
		isPinned(config) - Check if desktop entry is pinned
		matchRule(rule) - Check if rule matches the desktop entry
		setCustoms(entry) - Set custom properties for the desktop entry
		getNoDisplay() - Returns NoDisplay value
		getName() - Returns Name or Custom name (if set)
		getCommandLine() - Returns Exec value
		getPath() - Returns path to desktop entry file
		getFilename() - Returns name of desktop entry file
		getIcon() - Returns string representation of entry's icon
	"""

	def __init__(self, path):
		self.entry = Gio.DesktopAppInfo.new_from_filename(path)
		self.customName = None

	def isBlacklisted(self, config):
		"""
		Check if desktop entry is blacklisted

		Parameters:
			config - Config object containing blacklist

		Returns:
		result - true if entry is blacklisted, false otherwise
		"""

		# Check every rule until one matches
		for rule in config.getBlacklist():
			if self.matchRule(rule):
				return True
		return False

	def indexOfPinned(self, config):
		"""
		Gets index of pinned entry

		Parameters:
			config - Config object containing list of pinned entries rules

		Returns:
		i - index of rule if entry is pinned, otherwise -1
		"""

		# Check every rule until one matches
		i = 0
		for rule in config.getPinned():
			if self.matchRule(rule):
				return i
			i += 1
		return -1;

	def matchRule(self, rule):
		"""
		Check if rule matches the desktop entry

		Parameters:
			rule - the rule for checking the entry

		Returns:
		result - true if rule matches the entry, false otherwise
		"""

		if not len(rule):
			return False

		match = True
		if "name" in rule:
			match &= True if re.search(rule["name"], self.getName()) else False
		if "exec" in rule:
			match &= True if re.search(rule["exec"], self.getCommandLine()) else False
		return match

	def getNoDisplay(self):
		"""Returns NoDisplay value"""
		return self.entry.get_nodisplay()

	def getName(self):
		"""Returns Name or Custom name (if set)"""
		if self.customName:
			return customName
		else:
			return self.entry.get_name()

	def getCommandLine(self):
		"""Returns Exec value"""
		return self.entry.get_commandline()

	def getFilename(self):
		"""Returns name of desktop entry file"""
		return Path(self.getPath()).name

	def getPath(self):
		"""Returns path to desktop entry file"""
		return self.entry.get_filename()

	def getIcon(self):
		"""Returns string representation of entry's icon"""
		try:
			icon = self.entry.get_icon()
			if not icon:
				return None
			if isinstance(icon, Gio.FileIcon):
				return icon.get_file().get_path()
			if isinstance(icon, Gio.ThemedIcon):
				return icon.get_names()[0]

		except AttributeError as e:
			print(f"[!] AttributeError while reading icon file of {self.getFilename()}.", file=sys.stderr)
			print(f"[!] {e}.", file=sys.stderr)
			return None


if __name__ == "__main__":
	main()