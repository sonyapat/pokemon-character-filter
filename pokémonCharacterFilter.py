import streamlit as st
import requests
import pandas as pd
import concurrent.futures

st.title("Pokémon Character Filter")

# --- Fetch Pokémon list ---
@st.cache_data
def fetch_pokemon_list(limit=150):
    """
    Fetch a list of Pokémon from the PokéAPI.
    
    Parameters:
        limit (int): Maximum number of Pokémon to retrieve. Default is 150.
    
    Returns:
        pd.DataFrame: DataFrame containing 'name' and 'url' for each Pokémon.
    """
    url = f"https://pokeapi.co/api/v2/pokemon?limit={limit}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return pd.DataFrame(data['results'])

# --- Fetch Pokémon details ---
def fetch_pokemon_details(url):
    """
    Fetch detailed information for a single Pokémon.
    
    Parameters:
        url (str): API endpoint for a specific Pokémon.
    
    Returns:
        dict: Contains the following keys:
            - 'name': Pokémon name (capitalized)
            - 'image': URL to the front sprite
            - 'types': List of Pokémon types
            - 'abilities': List of Pokémon abilities
            - 'base_experience': Base experience value
        Returns None if the request fails.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return {
            'name': data['name'].capitalize(),
            'image': data['sprites']['front_default'],
            'types': [t['type']['name'] for t in data['types']],
            'abilities': [a['ability']['name'] for a in data['abilities']],
            'base_experience': data['base_experience'],
        }
    except:
        return None

# --- Fetch all details concurrently ---
@st.cache_data
def fetch_all_details(pokemon_list):
    """
    Fetch detailed information for all Pokémon in a list concurrently.
    
    Parameters:
        pokemon_list (pd.DataFrame): DataFrame with 'name' and 'url' columns.
    
    Returns:
        pd.DataFrame: DataFrame containing detailed Pokémon info for all Pokémon
        that have an available image.
    """
    details = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(fetch_pokemon_details, row['url']) for _, row in pokemon_list.iterrows()]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result and result['image']:
                details.append(result)
    return pd.DataFrame(details)

# --- Main App Logic ---
pokemon_list = fetch_pokemon_list()

if pokemon_list.empty:
    st.write("No Pokémon data available.")
else:
    # Fetch detailed Pokémon data
    df = fetch_all_details(pokemon_list)

    # --- Sidebar Filters ---
    st.sidebar.header("Filter Options")

    # Type filter (case-insensitive)
    all_types = sorted({t.lower() for sublist in df['types'] for t in sublist})
    type_options = ["all"] + all_types
    selected_type = st.sidebar.selectbox("Select Type", type_options).lower()

    # Ability filter (case-insensitive)
    all_abilities = sorted({a.lower() for sublist in df['abilities'] for a in sublist})
    ability_options = ["all"] + all_abilities
    selected_ability = st.sidebar.selectbox("Select Ability", ability_options).lower()

    st.subheader("Pokémon")

    # --- Apply Filters ---
    filtered_df = df
    if selected_type != "all":
        filtered_df = filtered_df[filtered_df['types'].apply(lambda types: selected_type in [t.lower() for t in types])]
    if selected_ability != "all":
        filtered_df = filtered_df[filtered_df['abilities'].apply(lambda abilities: selected_ability in [a.lower() for a in abilities])]

    # --- Display Pokémon in a grid layout ---
    if not filtered_df.empty:
        num_columns = 4
        for i in range(0, len(filtered_df), num_columns):
            row = filtered_df.iloc[i:i+num_columns]
            cols = st.columns(len(row))
            for col, (_, pokemon) in zip(cols, row.iterrows()):
                with col:
                    st.image(pokemon["image"], caption=pokemon["name"], width=150)
                    st.write(f"**Types:** {', '.join(t.capitalize() for t in pokemon['types'])}")
                    st.write(f"**Abilities:** {', '.join(a.capitalize() for a in pokemon['abilities'])}")
                    st.write(f"**Base Exp:** {pokemon['base_experience']}")
    else:
        st.write("No Pokémon match the selected filters.")