<script>
	import '../app.css';
	import PathVisualization from '$lib/PathVisualization.svelte';
	import TypeaheadInput from '$lib/TypeaheadInput.svelte';

	let username = '';
	let pathData = null;
	let loading = false;
	let error = '';
	let lastRefreshed = null;
	let storingFrom = null;

	// Load data tracking from database on mount
	async function loadMetadata() {
		try {
			const response = await fetch('/api/metadata');
			if (response.ok) {
				const metadata = await response.json();
				if (metadata) {
					lastRefreshed = metadata.last_refreshed ? new Date(metadata.last_refreshed) : null;
					storingFrom = metadata.storing_from ? new Date(metadata.storing_from) : null;
				}
			}
		} catch (err) {
			console.error('Failed to load metadata:', err);
		}
	}

	// Load metadata on component mount
	loadMetadata();

	async function searchPath() {
		if (!username.trim()) return;
		
		loading = true;
		error = '';
		
		try {
			const response = await fetch(`/api/path/${username.toLowerCase()}`);
			if (!response.ok) {
				throw new Error('Player not found or no path to Magnus');
			}
			pathData = await response.json();
			
			// If no path found, create a fallback showing the searched player and Magnus
			if (!pathData.path) {
				// Fetch avatars for both players
				let userAvatar = null;
				let magnusAvatar = null;
				
				try {
					// Fetch searched user's avatar
					const userResponse = await fetch(`https://api.chess.com/pub/player/${username.toLowerCase()}`);
					if (userResponse.ok) {
						const userProfile = await userResponse.json();
						userAvatar = userProfile.avatar || null;
					}
				} catch (e) {
					// If fetching fails, avatar remains null
				}
				
				try {
					// Fetch Magnus's avatar
					const magnusResponse = await fetch('https://api.chess.com/pub/player/magnuscarlsen');
					if (magnusResponse.ok) {
						const magnusProfile = await magnusResponse.json();
						magnusAvatar = magnusProfile.avatar || null;
					}
				} catch (e) {
					// If fetching fails, avatar remains null
				}
				
				pathData = {
					path: [
						{ username: username.toLowerCase(), avatar: userAvatar },
						{ username: 'magnuscarlsen', avatar: magnusAvatar }
					],
					games: null,
					noConnection: true
				};
			}
		} catch (err) {
			error = err.message;
			pathData = null;
		} finally {
			loading = false;
		}
	}

</script>

<main class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
	<div class="container mx-auto px-4 py-8">
		<header class="text-center mb-12">
			<h1 class="text-4xl font-bold text-gray-900 mb-4">
				Degrees of Magnus Carlsen
			</h1>
			<p class="text-lg text-gray-600 max-w-2xl mx-auto">
				Find the shortest path from any chess player to Magnus Carlsen through their games.
				Like Six Degrees of Kevin Bacon, but for chess!
			</p>
		</header>

		<section class="max-w-4xl mx-auto">
			<div class="bg-white rounded-lg shadow-lg p-6 mb-8">
				<h2 class="text-2xl font-semibold text-gray-800 mb-4">Find Your Path to Magnus</h2>
				
				<div class="mb-4">
					<TypeaheadInput
						bind:value={username}
						placeholder="Enter Chess.com username"
						onSearch={searchPath}
						disabled={loading}
					/>
					<button
						on:click={searchPath}
						disabled={loading}
						class="mt-3 w-full px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
					>
						{loading ? 'Searching...' : 'Find Path'}
					</button>
				</div>


				{#if error}
					<div class="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
						{error}
					</div>
				{/if}
			</div>

			{#if pathData && pathData.path}
				<PathVisualization {pathData} />
			{/if}
		</section>
	</div>
	
	<!-- Data info overlay -->
	{#if lastRefreshed && storingFrom}
		<div class="fixed bottom-4 right-4 text-xs text-gray-400 bg-white/80 backdrop-blur-sm rounded-lg px-3 py-2 shadow-sm">
			<div>Data last refreshed: {lastRefreshed.toLocaleString()}</div>
			<div>Storing games from: {storingFrom.toLocaleDateString()}</div>
		</div>
	{/if}
</main>
