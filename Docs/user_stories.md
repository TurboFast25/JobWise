Stories
1. As a home cook, I want to rate recipes on my personal scale relative to my other ratings, so that my scores can guide others to better recipes.
2. As a fan of Gordon Ramsey, I want to find and follow his highly rated recipes, so that my home cooking can be as good as his. 
3. As a busy parent, I want to sort ratings and find a good recipe as quickly as possible, so that I can minimize the time it takes to cook dinner.
4. As a user with allergies, I want to filter by my various allergens to find recipes that accommodate my needs, so that I can quickly find good recipes that I can safely eat.
5. I’m currently looking to lose weight, so finding recipes that can be nutritious and still taste good are a priority. 
6. Eating out has gotten too expensive, I want to recreate the dishes I’ve had at restaurants and make it for the fraction of a price I’d get outside. 
7. As a professional chef who was recently fired from a restaurant that treated me unfairly, I want to share the secrets of all recipes.
8. I am currently studying abroad at Omar Bongo University in Gabon. The food I am learning to make here is amazing and I want to share it with my friends and family back home in Azerbaijan.
9. As a foodie, when I try to rate a recipe but my ranking conflicts with my existing list (e.g., duplicate position), I want the system to prompt me to reorder my rankings, so that my list remains consistent.
10. As a fan of various celebrity chefs, when I try to follow a chef who does not exist or has no recipes in the system, I want to be notified gracefully, so that I understand why no results are shown.
11. As a college student, when I try to sort recipes but the system fails to load results, I want to see a fallback list (e.g., trending recipes), so that I can still quickly choose something to cook.
12. As a user with picky taste, when I apply filters that return no matching recipes, I want the system to suggest similar alternatives, so that I am not left with an empty experience.

Exceptions
1. Duplicate URL submission: If a user tries to add a recipe that already exists in the system, the user will be notified that recipe already exists and will be directed to the existing recipe.
2. Invalid URL submission: If a user tries to add a recipe with an invalid URL that cannot be reached, the system will return an error notifying the user the link is broken and ask them to try again or add the recipe details manually.
3. Rating without making: If a user tries to rate a recipe that they have not verified as having made themselves, the system will return an error notifying the user they have not logged the recipe as made and will ask them to do so before rating the recipe.
4. Conflicting dietary tags: For example, if a recipe is tagged as dairy free but contains a dairy product, the user will be notified of the conflict and ask the user to verify their filer/recipe to fix the conflict.
5. Same Username: If a user has the same username (not display name), prompt with an error saying the name is already taken.
6. Email Already Registered: If a user is creating a new account and the email is already linked to an existing user, prompt user with “email already registered” 
7. Recipe Upload Failure: If a user attempts to upload a recipe but required fields (ingredients, steps) are missing, the system will return an error prompting them to complete the missing information.
8. Follow Action Failure: If a user tries to follow another user they are already following, the system will notify them that they are already following that user.
9. Network / Server Failure: If a request fails due to a network or server issue, the system will notify the user that the action could not be completed and prompt them to retry.
10. Review Submission Failure: If a user submits a review with missing required fields (e.g., no text or invalid rating), the system will return an error prompting the user to complete all required fields.
11. Unauthorized List Modification: If a user attempts to edit or delete another user’s list or rankings, the system will return an error notifying the user they do not have permission to perform that action.
12. Invalid Allergy Filter Combination: If a user applies conflicting or overly restrictive allergy filters that result in no valid recipes, the system will notify the user and suggest adjusting their filters.
