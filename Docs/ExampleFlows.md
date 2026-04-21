# Example Flows

## Recipe Discovery Example Flow

Jennifer wants to find a good Italian recipe but does not trust generic ratings from random users. First, Jennifer checks a user she respects by calling GET /users/200. She sees that this user has a high trust authority score, so she decides to follow them by calling POST /social/follows.

After following the user, Jennifer requests a personalized Italian feed by calling GET /feed with the category set to Italian. In the results, she sees a recipe for "Miso Carbonara" ranked highly because it was reviewed by users she trusts.

Jennifer then opens the recipe by calling GET /recipes/42 to view the ingredients and instructions.

Jennifer decides to save the recipe. To do so she:

- starts by calling POST /cookbook and passes in a recipe_id of 42.
- receives confirmation that the recipe has been saved.

Jennifer now has a trusted recipe saved and is ready to cook it later using the app.

--------------------------------------------------------------------------------------------------------------

## Cook and Review Example Flow

Diego has just finished cooking a spicy ramen recipe and wants to leave a review. First, Diego retrieves the recipe details by calling GET /recipes/42 to make sure he is reviewing the correct recipe.

Diego then submits his review by calling POST /reviews and passes in a score of 7.5 along with a short comment. The system processes the review and calculates a normalized score based on Diego’s rating history.

Diego then checks his saved recipes by calling GET /cookbook and sees that the ramen now ranks highly in his personal list.

To save the recipe for later, Diego:
- calls POST /cookbook and passes in the recipe_id of 42.
- receives confirmation that the recipe has been saved.

Diego has now reviewed and saved the recipe in the app.

--------------------------------------------------------------------------------------------------------------

## Recipe Ingestion Example Flow

Louis finds a tomato sauce recipe online and wants to add it to the app. He submits the recipe by calling POST /recipes/ingest and includes the title and ingredients.

The system compares the recipe with existing entries and determines that it matches a recipe that already exists. Instead of creating a duplicate, the system returns a canonical recipe ID.

Louis then retrieves the recipe by calling GET /recipes/88 to confirm it is correct.

Louis decides to save it. To do so he:

- calls POST /cookbook and passes in the recipe_id of 88.
- receives confirmation that the recipe has been saved.

Louis successfully adds the recipe without creating duplicates and saves it in the app.

--------------------------------------------------------------------------------------------------------------
