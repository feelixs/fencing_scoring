#!/bin/bash

api_key_1="x"                              
api_key_2="y"
api_key_3="z"
api_key_4="a"

# Base arguments for aider
aider_args=(--model gemini/gemini-2.5-pro-exp-03-25)

# Determine which API key to use (default: 1)
key_number=1
if [ -n "$1" ]; then
  # Use the provided number if it's between 1 and 4
  if [[ "$1" =~ ^[1-4]$ ]]; then
    key_number=$1
  else
    echo "Invalid key number. Using default key 1."
  fi
fi

# Select the appropriate API key based on key_number
api_key_var="api_key_${key_number}"
selected_key=${!api_key_var}

# Add the API key to the arguments
aider_args+=(--api-key gemini="$selected_key")

# Execute aider with the constructed arguments
echo "Using API key ${key_number}"
echo aider "${aider_args[@]}" 
aider "${aider_args[@]}"

