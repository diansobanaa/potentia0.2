const { getDefaultConfig } = require("expo/metro-config");
const { withNativeWind } = require("nativewind/metro");

const config = getDefaultConfig(__dirname);

// Keep transformer as-is but enable ESM support and inline requires
config.transformer = {
	...config.transformer,
	getTransformOptions: async () => ({
		transform: {
			experimentalImportSupport: true,
			inlineRequires: true,
		},
	}),
};

// Prefer CJS over ESM to avoid `import.meta` in some deps on web
config.resolver = {
	...config.resolver,
	sourceExts: [...(config.resolver?.sourceExts || []), 'mjs', 'cjs'],
	unstable_conditionNames: ['browser', 'require', 'react-native'],
};

module.exports = withNativeWind(config, {
	input: "./app/global.css",
});
