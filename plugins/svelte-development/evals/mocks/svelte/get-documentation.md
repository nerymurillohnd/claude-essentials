<!-- Excerpts of the official Svelte and SvelteKit documentation (MIT), downloaded from https://svelte.dev/docs/<area>/<slug>/llms.txt; the eval returns them for any section. -->

# svelte/$props

The inputs to a component are referred to as _props_, which is short for _properties_. You pass props to components just like you pass attributes to elements:

```svelte
<!--- file: App.svelte --->
<script>
	import MyComponent from './MyComponent.svelte';
</script>

<MyComponent adjective="cool" />
```

On the other side, inside `MyComponent.svelte`, we can receive props with the `$props` rune...

```svelte
<!--- file: MyComponent.svelte --->
<script>
	let props = $props();
</script>

<p>this component is {props.adjective}</p>
```

...though more commonly, you'll [_destructure_](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Destructuring_assignment) your props:

```svelte
<!--- file: MyComponent.svelte --->
<script>
	let +++{ adjective }+++ = $props();
</script>

<p>this component is {+++adjective+++}</p>
```

## Fallback values

Destructuring allows us to declare fallback values, which are used if the parent component does not set a given prop (or the value is `undefined`):

```js
let { adjective = "happy" } = $props();
```

> [!NOTE] Fallback values are not turned into reactive state proxies (see [Updating props](#Updating-props) for more info)

## Renaming props

We can also use the destructuring assignment to rename props, which is necessary if they're invalid identifiers, or a JavaScript keyword like `super`:

```js
let { super: trouper = "lights are gonna find me" } = $props();
```

## Rest props

Finally, we can use a _rest property_ to get, well, the rest of the props:

```js
let { a, b, c, ...others } = $props();
```

[...]

## Type safety

You can add type safety to your components by annotating your props, as you would with any other variable declaration. In TypeScript that might look like this...

```svelte
<script lang="ts">
	let { adjective }: { adjective: string } = $props();
</script>
```

# svelte/snippet

```svelte
<!--- copy: false  --->
{#snippet name()}...{/snippet}
```

```svelte
<!--- copy: false  --->
{#snippet name(param1, param2, paramN)}...{/snippet}
```

Snippets, and [render tags](https://svelte.dev/docs/svelte/@render), are a way to create reusable chunks of markup inside your components. Instead of writing duplicative code like this...

```svelte
{#each images as image}
	{#if image.href}
		<a href={image.href}>
			<figure>
				<img src={image.src} alt={image.caption} width={image.width} height={image.height} />
				<figcaption>{image.caption}</figcaption>
			</figure>
		</a>
	{:else}
		<figure>
			<img src={image.src} alt={image.caption} width={image.width} height={image.height} />
			<figcaption>{image.caption}</figcaption>
		</figure>
	{/if}
{/each}
```

...you can write this:

```svelte
{#snippet figure(image)}
	<figure>
		<img src={image.src} alt={image.caption} width={image.width} height={image.height} />
		<figcaption>{image.caption}</figcaption>
	</figure>
{/snippet}

{#each images as image}
	{#if image.href}
		<a href={image.href}>
			{@render figure(image)}
		</a>
	{:else}
		{@render figure(image)}
	{/if}
{/each}
```

Like function declarations, snippets can have an arbitrary number of parameters, which can have default values, and you can destructure each parameter. You cannot use rest parameters, however.

[...]

## Passing snippets to components

### Explicit props

Within the template, snippets are values just like any other. As such, they can be passed to components as props:

<!-- codeblock:start {"title":"Explicit snippet props"} -->

```svelte
<!--- file: App.svelte --->
<script>
	import Table from './Table.svelte';

	const fruits = [
		{ name: 'apples', qty: 5, price: 2 },
		{ name: 'bananas', qty: 10, price: 1 },
		{ name: 'cherries', qty: 20, price: 0.5 }
	];
</script>

{#snippet header()}
	<th>fruit</th>
	<th>qty</th>
	<th>price</th>
	<th>total</th>
{/snippet}

{#snippet row(d)}
	<td>{d.name}</td>
	<td>{d.qty}</td>
	<td>{d.price}</td>
	<td>{d.qty * d.price}</td>
{/snippet}

<Table data={fruits} +++{header} {row}+++ />
```

```svelte
<!--- file: Table.svelte --->
<script>
	let { data, header, row } = $props();
</script>

<table>
	{#if header}
		<thead>
			<tr>{@render header()}</tr>
		</thead>
	{/if}

	<tbody>
		{#each data as d}
			<tr>{@render row(d)}</tr>
		{/each}
	</tbody>
</table>

<style>
	table {
		text-align: left;
		border-spacing: 0;
	}

	tbody tr:nth-child(2n+1) {
		background: ButtonFace;
	}

	table :global(th), table :global(td) {
		padding: 0.5em;
	}
</style>
```

<!-- codeblock:end -->

Think about it like passing content instead of data to a component. The concept is similar to slots in web components.

### Implicit props

As an authoring convenience, snippets declared directly _inside_ a component implicitly become props _on_ the component:

<!-- codeblock:start {"title":"Implicit snippet props"} -->

```svelte
<!--- file: App.svelte --->
<script>
	import Table from './Table.svelte';

	const fruits = [
		{ name: 'apples', qty: 5, price: 2 },
		{ name: 'bananas', qty: 10, price: 1 },
		{ name: 'cherries', qty: 20, price: 0.5 }
	];
</script>

<Table data={fruits}>
	{#snippet header()}
		<th>fruit</th>
		<th>qty</th>
		<th>price</th>
		<th>total</th>
	{/snippet}

	{#snippet row(d)}
		<td>{d.name}</td>
		<td>{d.qty}</td>
		<td>{d.price}</td>
		<td>{d.qty * d.price}</td>
	{/snippet}
</Table>
```

```svelte
<!--- file: Table.svelte --->
<script>
	let { data, header, row } = $props();
</script>

<table>
	{#if header}
		<thead>
			<tr>{@render header()}</tr>
		</thead>
	{/if}

	<tbody>
		{#each data as d}
			<tr>{@render row(d)}</tr>
		{/each}
	</tbody>
</table>

<style>
	table {
		text-align: left;
		border-spacing: 0;
	}

	tbody tr:nth-child(2n+1) {
		background: ButtonFace;
	}

	table :global(th), table :global(td) {
		padding: 0.5em;
	}
</style>
```

<!-- codeblock:end -->

### Implicit `children` snippet

Any content inside the component tags that is _not_ a snippet declaration implicitly becomes part of the `children` snippet:

<!-- codeblock:start {"title":"Implicit children snippet","selected":"Button.svelte"} -->

```svelte
<!--- file: App.svelte --->
<script>
	import Button from './Button.svelte';
</script>

<Button>click me</Button>
```

```svelte
<!--- file: Button.svelte --->
<script>
	let { children } = $props();
</script>

<!-- result will be <button>click me</button> -->
<button>{@render children()}</button>
```

<!-- codeblock:end -->

> [!NOTE] Note that you cannot have a prop called `children` if you also have content inside the component — for this reason, you should avoid having props with that name

### Optional snippet props

You can declare snippet props as being optional. You can either use optional chaining to not render anything if the snippet isn't set...

```svelte
<script>
    let { children } = $props();
</script>

{@render children?.()}
```

...or use an `#if` block to render fallback content:

```svelte
<script>
    let { children } = $props();
</script>

{#if children}
    {@render children()}
{:else}
    fallback content
{/if}
```

# svelte/basic-markup (Events)

## Events

Listening to DOM events is possible by adding attributes to the element that start with `on`. For example, to listen to the `click` event, add the `onclick` attribute to a button:

```svelte
<button onclick={() => console.log('clicked')}>click me</button>
```

Event attributes are case sensitive. `onclick` listens to the `click` event, `onClick` listens to the `Click` event, which is different. This ensures you can listen to custom events that have uppercase characters in them.

Because events are just attributes, the same rules as for attributes apply:

- you can use the shorthand form: `<button {onclick}>click me</button>`
- you can spread them: `<button {...thisSpreadContainsEventAttributes}>click me</button>`

Timing-wise, event attributes always fire after events from bindings (e.g. `oninput` always fires after an update to `bind:value`). Under the hood, some event handlers are attached directly with `addEventListener`, while others are _delegated_.

When using `ontouchstart` and `ontouchmove` event attributes, the handlers are [passive](https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener#using_passive_listeners) for better performance. This greatly improves responsiveness by allowing the browser to scroll the document immediately, rather than waiting to see if the event handler calls `event.preventDefault()`.

In the very rare cases that you need to prevent these event defaults, you should use [`on`](https://svelte.dev/docs/svelte/svelte-events#on) instead (for example inside an action).

### Event delegation

To reduce memory footprint and increase performance, Svelte uses a technique called event delegation. This means that for certain events — see the list below — a single event listener at the application root takes responsibility for running any handlers on the event's path.

There are a few gotchas to be aware of:

- when you manually dispatch an event with a delegated listener, make sure to set the `{ bubbles: true }` option or it won't reach the application root
- when using `addEventListener` directly, avoid calling `stopPropagation` or the event won't reach the application root and handlers won't be invoked. Similarly, handlers added manually inside the application root will run _before_ handlers added declaratively deeper in the DOM (with e.g. `onclick={...}`), in both capturing and bubbling phases. For these reasons it's better to use the `on` function imported from `svelte/events` rather than `addEventListener`, as it will ensure that order is preserved and `stopPropagation` is handled correctly.

The following event handlers are delegated:

- `beforeinput`
- `click`
- `change`
- `dblclick`
- `contextmenu`
- `focusin`
- `focusout`
- `input`
- `keydown`
- `keyup`
- `mousedown`
- `mousemove`
- `mouseout`
- `mouseover`
- `mouseup`
- `pointerdown`
- `pointermove`
- `pointerout`
- `pointerover`
- `pointerup`
- `touchend`
- `touchmove`
- `touchstart`

# svelte/each

```svelte
<!--- copy: false  --->
{#each expression as name}...{/each}
```

```svelte
<!--- copy: false  --->
{#each expression as name, index}...{/each}
```

Iterating over values can be done with an each block. The values in question can be arrays, array-like objects (i.e. anything with a `length` property), or iterables like `Map` and `Set`. (Internally, they are converted to arrays with [`Array.from`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/from).)

If the value is `null` or `undefined`, it is treated the same as an empty array (which will cause [else blocks](#Else-blocks) to be rendered, where applicable).

```svelte
<h1>Shopping list</h1>
<ul>
	{#each items as item}
		<li>{item.name} x {item.qty}</li>
	{/each}
</ul>
```

An each block can also specify an _index_, equivalent to the second argument in an `array.map(...)` callback:

```svelte
{#each items as item, i}
	<li>{i + 1}: {item.name} x {item.qty}</li>
{/each}
```

## Keyed each blocks

```svelte
<!--- copy: false  --->
{#each expression as name (key)}...{/each}
```

```svelte
<!--- copy: false  --->
{#each expression as name, index (key)}...{/each}
```

If a _key_ expression is provided — which must uniquely identify each list item — Svelte will use it to intelligently update the list when data changes by inserting, moving and deleting items, rather than adding or removing items at the end and updating the state in the middle.

The key can be any object, but strings and numbers are recommended since they allow identity to persist when the objects themselves change.

```svelte
{#each items as item (item.id)}
	<li>{item.name} x {item.qty}</li>
{/each}

<!-- or with additional index value -->
{#each items as item, i (item.id)}
	<li>{i + 1}: {item.name} x {item.qty}</li>
{/each}
```

You can freely use destructuring and rest patterns in each blocks.

```svelte
{#each items as { id, name, qty }, i (id)}
	<li>{i + 1}: {name} x {qty}</li>
{/each}

{#each objects as { id, ...rest }}
	<li><span>{id}</span><MyComponent {...rest} /></li>
{/each}

{#each items as [id, ...rest]}
	<li><span>{id}</span><MyComponent values={rest} /></li>
{/each}
```

# kit/advanced-routing (Matching)

## Matching

A route like `src/routes/fruits/[page]` would match `/fruits/apple`, but it would also match `/fruits/rocketship`. We don't want that. You can ensure that route parameters are well-formed by adding a _matcher_ to your `src/params.js` file (or `src/params.ts`)...

```js
/// file: src/params.js
import { defineParams } from "@sveltejs/kit/params";

export const params = defineParams({
  fruit: (param) => {
    if (param !== "apple" && param !== "orange") return;
    return param;
  },
});
```

...and augmenting your routes:

```
src/routes/fruits/[page+++=fruit+++]
```

If the pathname doesn't match, SvelteKit will try to match other routes (using the sort order specified below), before eventually returning a 404. If it does match, the returned value is passed as the param value.

You can also use a [Standard Schema](https://standardschema.dev) — for example with [Valibot](https://valibot.dev):

```js
/// file: src/params.js
import { defineParams } from "@sveltejs/kit/params";
import * as v from "valibot";

export const params = defineParams({
  number: v.pipe(v.string(), v.toNumber()),
});
```

If validation fails, the route does not match. If it succeeds, the param is typed with the output type of the schema, which must extend `string`, `boolean`, `number` (as in the example above) or `bigint`:

```js
/// file: src/routes/items/[id=number]/+page.js
/** @type {import('./$types').PageLoad} */
export function load({ params }) {
  console.log(typeof params.id); // 'number'
}
```

Transformations should be _symmetrical_ — if converting to a number, then calling `toString()` on that number should return the original string. This allows the [`resolve`](https://svelte.dev/docs/kit/$app-paths#resolve) function to construct a pathname correctly:

```js
import { resolve } from "$app/paths";

resolve("/blog/[id=number]", { id: 1 });
```

> [!NOTE] Matchers run both on the server and in the browser.

> [!NOTE] Prior to SvelteKit 3, you had to define each param matcher in a separate file, all listed under a `params` folder (for example `src/params/foo.js` with `export const match = (param) => param === 'foo';`), and matching was determined by whether or not the matcher returns a truthy value (which means no value transformation took place).

# kit/@sveltejs-kit-params

```js
// @noErrors
import { defineParams } from "@sveltejs/kit/params";
```

## defineParams

Define [parameter matchers](https://svelte.dev/docs/kit/advanced-routing#Matching) for your app.

<div class="ts-block">

```dts
function defineParams<
	T extends Record<string, ParamDefinition>
>(definitions: T): DefinedParams<T>;
```

</div>

## DefinedParams

The return type of [`defineParams`](https://svelte.dev/docs/kit/@sveltejs-kit-params#defineParams).

<div class="ts-block">

```dts
type DefinedParams<
	T extends Record<string, ParamDefinition>
> = {
	readonly [K in keyof T]: ParamEntry<T[K]>;
};
```

</div>

## MatcherParam

Extracts the param type from a matcher.

<div class="ts-block">

```dts
type MatcherParam<M extends StandardSchemaV1<any, any>> =
	M extends StandardSchemaV1<any, infer Inner>
		? Inner extends ParamValue
			? Inner
			: Inner extends StandardSchemaV1<any, any>
				? StandardSchemaV1.InferOutput<Inner> extends ParamValue
					? StandardSchemaV1.InferOutput<Inner>
					: never
				: never
		: never;
```

</div>

## ParamDefinition

A param matcher definition passed to [`defineParams`](https://svelte.dev/docs/kit/@sveltejs-kit-params#defineParams).

<div class="ts-block">

```dts
type ParamDefinition =
	| ((param: string) => ParamValue | undefined)
	| StandardSchemaV1<string, ParamValue>;
```

</div>

## ParamMatcher

The shape of a param matcher. See [matching](https://svelte.dev/docs/kit/advanced-routing#Matching) for more info.

<div class="ts-block">

```dts
type ParamMatcher<Output = any> = StandardSchemaV1<
	string,
	Output
>;
```

</div>

## ParamValue

A value that can be parsed from a URL param and losslessly encoded with `String(...)`.

<div class="ts-block">

```dts
type ParamValue = string | number | boolean | bigint;
```

</div>
